import argparse
import sys
import os
import random
from typing import List

from dagopt.tac import parse_tac, Instr
from dagopt.blocks import build_blocks
from dagopt.dag import build_dag, get_live_nodes
from dagopt.liveness import compute_live_out
from dagopt.codegen import CodeGenerator, get_terminator_operands
from dagopt.dotexport import export_dot
from dagopt.verify import verify_block
from dagopt.metrics import BlockMetrics, TotalMetrics, print_metrics_table, export_metrics_csv, export_metrics_json

def count_arith(instrs: List[Instr]) -> int:
    return sum(1 for i in instrs if i.kind == 'binary' and i.op in ('+', '-', '*', '/'))

def count_copy(instrs: List[Instr]) -> int:
    return sum(1 for i in instrs if i.kind == 'copy')

def optimize_program(args, input_text: str):
    if args.seed is not None:
        random.seed(args.seed)
        
    instrs = parse_tac(input_text)
    blocks = build_blocks(instrs)
    
    optimized_instrs = []
    block_metrics_list = []
    
    total = TotalMetrics()
    
    if args.dot_dir:
        os.makedirs(args.dot_dir, exist_ok=True)
        
    for i, block in enumerate(blocks):
        # Metrics before
        b_instrs_in = len(block.instrs) + (1 if block.terminator else 0)
        b_arith_in = count_arith(block.instrs)
        b_copy_in = count_copy(block.instrs)
        
        override_live = None
        if args.live_out:
            override_live = set(args.live_out.split(','))
            
        live_out = compute_live_out(block, args.temp_regex, override_live)
        
        dag = build_dag(block.instrs, args.no_fold, args.no_algebra, args.no_commute)
        
        terminator_reads = set()
        if block.terminator:
            for op in get_terminator_operands(block.terminator):
                if isinstance(op, str):
                    terminator_reads.add(op)
                    
        live_nodes = get_live_nodes(dag, live_out, terminator_reads)
        
        # Dead nodes removed: dag.nodes len - live_nodes len
        dead_removed = len(dag.nodes) - len(live_nodes)
        
        cg = CodeGenerator(dag, live_nodes, live_out, args.temp_regex, block.terminator)
        new_instrs = cg.generate()
        
        # Metrics after
        b_instrs_out = len(new_instrs)
        b_arith_out = count_arith(new_instrs)
        b_copy_out = count_copy(new_instrs)
        
        verification_passed = True
        if args.verify > 0:
            if not verify_block(block.instrs, new_instrs, live_out, args.verify):
                verification_passed = False
                total.total_verification_passed = False
                if not args.quiet:
                    print(f"WARNING: Verification failed for block {i}", file=sys.stderr)
        
        bm = BlockMetrics(
            block_id=i,
            instrs_before=b_instrs_in,
            instrs_after=b_instrs_out,
            arith_before=b_arith_in,
            arith_after=b_arith_out,
            copy_before=b_copy_in,
            copy_after=b_copy_out,
            dag_nodes=len(dag.nodes),
            cse_hits=dag.cse_hits,
            constants_folded=dag.constants_folded,
            algebraic_simplifications=dag.algebraic_simplifications,
            dead_nodes_removed=dead_removed,
            verification_passed=verification_passed
        )
        block_metrics_list.append(bm)
        
        total.total_instrs_before += b_instrs_in
        total.total_instrs_after += b_instrs_out
        total.total_arith_before += b_arith_in
        total.total_arith_after += b_arith_out
        total.total_copy_before += b_copy_in
        total.total_copy_after += b_copy_out
        total.total_dag_nodes += len(dag.nodes)
        total.total_cse_hits += dag.cse_hits
        total.total_constants_folded += dag.constants_folded
        total.total_algebraic_simplifications += dag.algebraic_simplifications
        total.total_dead_nodes_removed += dead_removed
        
        optimized_instrs.extend(new_instrs)
        
        if args.dot_dir:
            dot_content = export_dot(dag, live_nodes)
            dot_file = os.path.join(args.dot_dir, f"block_{i}.dot")
            with open(dot_file, 'w') as f:
                f.write(dot_content)
                
    if args.o:
        with open(args.o, 'w') as f:
            for instr in optimized_instrs:
                f.write(str(instr) + "\n")
    else:
        if not args.quiet:
            for instr in optimized_instrs:
                print(str(instr))
                
    if args.metrics:
        if not args.quiet:
            print_metrics_table(block_metrics_list, total)
        export_metrics_json(block_metrics_list, total, "metrics.json")
        export_metrics_csv(block_metrics_list, total, "metrics.csv")

def main():
    parser = argparse.ArgumentParser(description="DAG-Based Basic Block Optimizer")
    parser.add_argument("input_file", help="Input TAC file")
    parser.add_argument("-o", metavar="FILE", help="Output optimized TAC file")
    parser.add_argument("--live-out", help="Comma-separated list of variables to consider live-out globally")
    parser.add_argument("--temp-regex", default=r"^_(t|n)\d+$", help="Regex for temporaries")
    parser.add_argument("--no-fold", action="store_true", help="Disable constant folding")
    parser.add_argument("--no-algebra", action="store_true", help="Disable algebraic simplifications")
    parser.add_argument("--no-commute", action="store_true", help="Disable commutativity canonicalization")
    parser.add_argument("--dot-dir", metavar="DIR", help="Export block DAGs to DIR")
    parser.add_argument("--verify", type=int, default=0, metavar="N", help="Run N random testing trials per block")
    parser.add_argument("--seed", type=int, help="Random seed for verification")
    parser.add_argument("--metrics", action="store_true", help="Collect and output metrics")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    
    args = parser.parse_args()
    
    with open(args.input_file, 'r') as f:
        input_text = f.read()
        
    optimize_program(args, input_text)

if __name__ == "__main__":
    main()
