"""
verify_demo.py — Step-by-step DAG verification walkthrough.

Shows every phase of the pipeline:
  1. Parse TAC
  2. Build basic blocks
  3. Build DAG (with optimizations)
  4. Liveness & dead-node pruning
  5. Code generation
  6. Random-input equivalence verification (fuzzer)

Run:
    python examples/verify_demo.py examples/example.tac
    python examples/verify_demo.py tests/cases/T05.tac
    python examples/verify_demo.py tests/cases/T01.tac
"""
import sys
import random
import argparse

# ── helpers ──────────────────────────────────────────────────────────────────

SEP  = "─" * 70
SEP2 = "═" * 70

def hdr(title: str):
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)

def sub(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verbose DAG verification demo")
    parser.add_argument("tac_file", help="Input .tac file")
    parser.add_argument("--trials",  type=int, default=50,  help="Random-test trials (default 50)")
    parser.add_argument("--seed",    type=int, default=42,  help="RNG seed (default 42)")
    parser.add_argument("--block",   type=int, default=0,   help="Block index to verify (default 0)")
    parser.add_argument("--live-out", default="",           help="Comma-separated live-out override")
    args = parser.parse_args()

    # ── imports ──────────────────────────────────────────────────────────────
    from dagopt.tac          import parse_tac, format_instr
    from dagopt.blocks       import build_blocks
    from dagopt.dag          import build_dag, get_live_nodes, dag_summary
    from dagopt.liveness     import compute_live_out
    from dagopt.codegen      import CodeGenerator, get_terminator_operands
    from dagopt.interp       import interpret_block, collect_reads_before_writes
    from dagopt.verify       import verify_block

    # ─────────────────────────────────────────────────────────────────────────
    hdr(f"PHASE 1 — Parse TAC   [{args.tac_file}]")
    # ─────────────────────────────────────────────────────────────────────────
    with open(args.tac_file) as f:
        text = f.read()

    instrs = parse_tac(text)
    print(f"\n  Parsed {len(instrs)} instruction(s):\n")
    for i, instr in enumerate(instrs):
        print(f"    [{i:2d}]  {format_instr(instr):<30}  kind={instr.kind}")

    # ─────────────────────────────────────────────────────────────────────────
    hdr("PHASE 2 — Build Basic Blocks")
    # ─────────────────────────────────────────────────────────────────────────
    blocks = build_blocks(instrs)
    print(f"\n  Found {len(blocks)} basic block(s):\n")
    for blk in blocks:
        term_str = f"  terminator → {format_instr(blk.terminator)}" if blk.terminator else ""
        print(f"  Block {blk.index}:  {len(blk.instrs)} interior instr(s){term_str}")
        for instr in blk.instrs:
            print(f"           {format_instr(instr)}")
        print(f"           successors={blk.successors}  predecessors={blk.predecessors}")

    if args.block >= len(blocks):
        print(f"\n  ✗  Block {args.block} does not exist.")
        sys.exit(1)

    block = blocks[args.block]
    print(f"\n  ► Working on Block {args.block}")

    # ─────────────────────────────────────────────────────────────────────────
    hdr("PHASE 3 — Liveness Analysis")
    # ─────────────────────────────────────────────────────────────────────────
    override = set(args.live_out.split(",")) if args.live_out else None
    live_out = compute_live_out(block, r"^_(t|n)\d+$", override)
    print(f"""
  Live-out variables (will be kept alive after the block):
    {sorted(live_out)}

  Rule: every non-temporary variable appearing in the block is live-out
  by default. Temporaries matching ^_(t|n)\\d+$ are excluded unless they
  are read by the block's terminator instruction.
""")

    # ─────────────────────────────────────────────────────────────────────────
    hdr("PHASE 4 — Build DAG")
    # ─────────────────────────────────────────────────────────────────────────
    dag = build_dag(block.instrs)

    print(f"""
  DAG construction processes instructions one-by-one:
    • Leaf nodes  : created for variables and constants (deduplicated).
    • Op nodes    : keyed by (operator, child_id_1, child_id_2).
      - Before inserting, try_simplify() is called:
          ◦ Constant folding   — both children are consts → fold to single const
          ◦ Algebraic identity — x*1→x, x+0→x, x-x→0, etc.
          ◦ Commutativity      — b+a gets same key as a+b (min/max child ids)
      - If the key already exists → CSE hit (no new node, counter++).
    • cur[x] mapping tracks which node each variable currently points to.

  DAG nodes (bottom = leaves, top = roots):
""")
    for line in dag_summary(dag).splitlines():
        print(f"    {line}")

    print(f"""
  ┌─────────────────────────────────────────────┐
  │  Total nodes      : {len(dag.nodes):>4}                      │
  │  CSE hits         : {dag.cse_hits:>4}  (redundant exprs)   │
  │  Constants folded : {dag.constants_folded:>4}  (compile-time arith) │
  │  Algebraic simplif: {dag.algebraic_simplifications:>4}  (x*1→x, x+0→x …)  │
  └─────────────────────────────────────────────┘""")

    # ─────────────────────────────────────────────────────────────────────────
    hdr("PHASE 5 — Dead-Node Pruning (Liveness on DAG)")
    # ─────────────────────────────────────────────────────────────────────────
    terminator_reads: set = set()
    if block.terminator:
        for op in get_terminator_operands(block.terminator):
            if isinstance(op, str):
                terminator_reads.add(op)

    live_nodes = get_live_nodes(dag, live_out, terminator_reads)
    dead_nodes = {n.id for n in dag.nodes} - live_nodes

    print(f"""
  Starting from every live-out variable's current DAG node, a reverse BFS
  marks all reachable ancestor nodes as LIVE.  Anything not reachable = DEAD.

  Live node IDs  : {sorted(live_nodes)}
  Dead node IDs  : {sorted(dead_nodes)}  ← will NOT be emitted
""")
    for n in dag.nodes:
        status = "LIVE" if n.id in live_nodes else "DEAD"
        labels = f"[{', '.join(n.labels)}]" if n.labels else ""
        print(f"    n{n.id:02d}  {status}  op={n.op:<8}  value={str(n.value):<8}  labels={labels}")

    # ─────────────────────────────────────────────────────────────────────────
    hdr("PHASE 6 — Code Generation")
    # ─────────────────────────────────────────────────────────────────────────
    cg = CodeGenerator(dag, live_nodes, live_out, r"^_(t|n)\d+$", block.terminator)
    opt_instrs = cg.generate()

    print(f"""
  CodeGenerator emits instructions for live nodes only, using a topological
  sort (Kahn's algorithm) that respects read-after-write (RAW) dependencies.
  Write-after-read (WAR) cycles are broken by inserting fresh _n# temporaries.

  Original block ({len(block.instrs)} instr):
""")
    for instr in block.instrs:
        print(f"    {format_instr(instr)}")

    print(f"\n  Optimized block ({len(opt_instrs)} instr):\n")
    for instr in opt_instrs:
        print(f"    {format_instr(instr)}")

    saved = len(block.instrs) - len(opt_instrs)
    pct   = 100 * saved / len(block.instrs) if block.instrs else 0
    print(f"\n  Instructions saved: {saved} / {len(block.instrs)}  ({pct:.0f}% reduction)")

    # ─────────────────────────────────────────────────────────────────────────
    hdr("PHASE 7 — Equivalence Verification (Random-Input Fuzzing)")
    # ─────────────────────────────────────────────────────────────────────────
    reads = collect_reads_before_writes(block.instrs)
    print(f"""
  The verifier works as follows:
    1. Identify all input variables (read before being written): {sorted(reads)}
    2. For each trial, sample random integer inputs (biased toward 0, 1, -1).
    3. Run the ORIGINAL block through the interpreter → orig_env
    4. Run the OPTIMIZED block through the interpreter → opt_env
    5. Assert that every live-out variable has the same value in both envs.

  Running {args.trials} trials with seed={args.seed} …
""")

    rng = random.Random(args.seed)
    trials_run = 0
    trials_skipped = 0
    failures = 0

    for trial_idx in range(args.trials):
        env = {}
        for r in reads:
            rv = rng.random()
            if rv < 0.1:   env[r] = 0
            elif rv < 0.2: env[r] = 1
            elif rv < 0.3: env[r] = -1
            else:          env[r] = rng.randint(-20, 20)

        from dagopt.interp import interpret_block
        from dagopt.tac    import safe_div

        try:
            orig_env = interpret_block(block.instrs, env)
        except ZeroDivisionError:
            trials_skipped += 1
            continue

        try:
            opt_env = interpret_block(opt_instrs, env)
        except ZeroDivisionError:
            failures += 1
            print(f"  ✗  Trial {trial_idx+1:3d}: FAIL — optimized faulted, original did not")
            print(f"         inputs  = {env}")
            continue

        mismatch = {v: (orig_env.get(v), opt_env.get(v))
                    for v in live_out
                    if v in orig_env and orig_env.get(v) != opt_env.get(v)}

        if mismatch:
            failures += 1
            print(f"  ✗  Trial {trial_idx+1:3d}: FAIL — live-out mismatch")
            print(f"         inputs      = {env}")
            print(f"         orig_env    = { {k: orig_env.get(k) for k in live_out} }")
            print(f"         opt_env     = { {k: opt_env.get(k)  for k in live_out} }")
            print(f"         mismatches  = {mismatch}")
        else:
            trials_run += 1

        # Print first 5 passing trials verbosely
        if trial_idx < 5:
            print(f"  ✓  Trial {trial_idx+1:3d}: inputs={env}")
            print(f"         orig live-out = { {k: orig_env.get(k) for k in sorted(live_out)} }")
            print(f"         opt  live-out = { {k: opt_env.get(k)  for k in sorted(live_out)} }")

    if trial_idx >= 5:
        print(f"  ... ({args.trials - 5} more trials, showing summary only)")

    # ─────────────────────────────────────────────────────────────────────────
    hdr("SUMMARY")
    # ─────────────────────────────────────────────────────────────────────────
    status_icon = "✓  PASSED" if failures == 0 else "✗  FAILED"
    print(f"""
  Block {args.block} — {args.tac_file}
  ┌──────────────────────────────────────────────────────┐
  │  DAG nodes          : {len(dag.nodes):>4}                         │
  │  CSE hits           : {dag.cse_hits:>4}                         │
  │  Constants folded   : {dag.constants_folded:>4}                         │
  │  Algebraic simplif  : {dag.algebraic_simplifications:>4}                         │
  │  Dead nodes pruned  : {len(dead_nodes):>4}                         │
  │  Instructions in    : {len(block.instrs):>4}                         │
  │  Instructions out   : {len(opt_instrs):>4}  ({pct:.0f}% reduction)       │
  │  Trials run         : {trials_run:>4}                         │
  │  Trials skipped     : {trials_skipped:>4}  (div-by-zero in orig)   │
  │  Failures           : {failures:>4}                         │
  │  Verification       :   {status_icon}                 │
  └──────────────────────────────────────────────────────┘
""")

if __name__ == "__main__":
    main()
