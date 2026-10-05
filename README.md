# DagOpt — DAG-Based Basic Block Optimizer

A command-line compiler-optimization tool that reads **three-address code (TAC)**, splits it into basic blocks, constructs a **Directed Acyclic Graph (DAG)** per block, and uses that DAG to:

- Eliminate **common subexpressions (CSE)**
- Fold **constants** at compile time
- Apply **algebraic identities** (e.g. `x * 1 → x`, `x + 0 → x`)
- Canonicalize **commutative** operations (`b + a` detected as `a + b`)
- Eliminate **dead code** (variables not live-out)

Optimized TAC is emitted with optional **Graphviz DOT export** and **per-block metrics**.

---

## Requirements

- Python 3.10+
- `graphviz` Python package (for DOT generation)

---

## Installation

```bash
# Enter the project directory
cd DagOpt

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# Install the package (editable) with dev dependencies
pip install -e ".[test]"
```

---

## Input Format — Three-Address Code (TAC)

Each non-blank, non-comment line is one of the following forms:

| Form | Example | Meaning |
|------|---------|---------|
| `x = y` | `a = b` | Copy or integer literal assignment |
| `x = - y` | `a = - b` | Unary negation |
| `x = y OP z` | `c = a + b` | Binary op: `+` `-` `*` `/` `%` |
| `L:` | `loop:` | Label declaration |
| `goto L` | `goto loop` | Unconditional branch |
| `if a REL b goto L` | `if x < 10 goto loop` | Conditional branch (`<` `<=` `>` `>=` `==` `!=`) |

- Operands are variable names matching `[A-Za-z_][A-Za-z0-9_]*` or integer literals.
- Lines beginning with `#` (or containing `#`) are treated as comments.

**Example — `example.tac`:**

```
# CSE + constant folding demo
a = 1
b = 2
c = a + b       # computed once
d = a + b       # CSE: reuses c's node
e = c * 1       # algebraic: e = c
f = b + a       # commutative: same as a + b, reuses node
```

---

## Usage

### Basic optimization (print to stdout)

```bash
python -m dagopt example.tac
```

### Write optimized output to a file

```bash
python -m dagopt example.tac -o optimized.tac
```

### Specify live-out variables

By default, only non-temporary variables are kept alive. Use `--live-out` to override:

```bash
python -m dagopt example.tac --live-out a,b,c,result
```

### Show optimization metrics

Prints a per-block summary table and writes `metrics.json` / `metrics.csv`:

```bash
python -m dagopt example.tac --metrics
```

### Export DAG visualizations (Graphviz DOT)

Writes one `.dot` file per basic block to the specified directory:

```bash
python -m dagopt example.tac --dot-dir ./graphs

# Render to PNG (requires the Graphviz `dot` binary)
dot -Tpng graphs/block_0.dot -o graphs/block_0.png
```

In the DOT graph:
- **Live nodes** are solid; dead nodes are dashed/grey.
- **Shared nodes** (CSE hits) are filled light-blue.
- Leaf boxes represent variables or constants.

### Verify correctness with random testing

Runs `N` random-input trials to check that the optimized block is semantically equivalent to the original:

```bash
python -m dagopt example.tac --verify 100 --seed 42
```

---

## All CLI Options

```
python -m dagopt <input_file> [options]

Positional:
  input_file          Path to the input .tac file

Output:
  -o FILE             Write optimized TAC to FILE instead of stdout
  --quiet             Suppress all stdout output

Optimization controls:
  --no-fold           Disable constant folding  (e.g. 2 + 3 stays as-is)
  --no-algebra        Disable algebraic simplifications  (x*1, x+0, etc.)
  --no-commute        Disable commutativity canonicalization  (b+a != a+b)

Live variable analysis:
  --live-out VARS     Comma-separated variables always considered live-out
  --temp-regex REGEX  Regex identifying temporaries (default: ^_(t|n)\d+$)

DAG visualization:
  --dot-dir DIR       Export per-block DAG .dot files to DIR

Metrics:
  --metrics           Print metrics table; write metrics.json + metrics.csv

Verification:
  --verify N          Run N random-input equivalence trials per block
  --seed INT          Fix the random seed for reproducible verification
```

---

## Metrics Table

When `--metrics` is passed:

```
Block    InstrIn   InstrOut   ArithIn   ArithOut   CopyIn   CopyOut   DAGNodes   CSE   ConstFold   Algebraic   DeadRm   Verify
-----------------------------------------------------------------------------------------------------------------------------
0        6         6          4         0          2        6         4          0     4           0           1        True
-----------------------------------------------------------------------------------------------------------------------------
TOTAL    6         6          4         0          2        6         4          0     4           0           1        True
```

| Column | Description |
|--------|-------------|
| `InstrIn` / `InstrOut` | Instruction count before / after optimization |
| `ArithIn` / `ArithOut` | Arithmetic operation count before / after |
| `CopyIn` / `CopyOut` | Copy/assignment count before / after |
| `DAGNodes` | Total nodes built in the DAG |
| `CSE` | Common-subexpression eliminations |
| `ConstFold` | Constants folded at compile time |
| `Algebraic` | Algebraic identity simplifications applied |
| `DeadRm` | Dead DAG nodes pruned |
| `Verify` | Whether random-input verification passed |

JSON and CSV copies are written to `metrics.json` and `metrics.csv` in the working directory.

---

## Running the Tests

```bash
pytest            # run all 35 tests
pytest -v         # verbose output
pytest tests/test_dag.py   # single module
```

| Test file | What it covers |
|-----------|----------------|
| `test_tac.py` | TAC parser, formatting, syntax errors |
| `test_blocks.py` | Basic block splitting, leader detection |
| `test_dag.py` | DAG construction, CSE hit counting |
| `test_simplify.py` | Constant folding, algebraic identities |
| `test_interp.py` | Straight-line interpreter, read-before-write |
| `test_verify.py` | Random equivalence checker |
| `test_codegen.py` | Code generation, cycle breaking |
| `test_dotexport.py` | DOT file structure validation |
| `test_metrics.py` | Metrics dataclass and table printing |
| `test_e2e.py` | End-to-end: optimize then verify across 15+ cases |

---

## Project Structure

```
DagOpt/
├── dagopt/
│   ├── tac.py          # TAC data structures & parser
│   ├── blocks.py       # Basic block splitting (build_blocks)
│   ├── dag.py          # DAG construction, CSE, simplification hooks
│   ├── simplify.py     # Constant folding & algebraic identities
│   ├── liveness.py     # Live-out variable analysis
│   ├── codegen.py      # Code generation from DAG (optimize_block)
│   ├── interp.py       # Straight-line interpreter (used by verifier)
│   ├── verify.py       # Random-input equivalence checker
│   ├── dotexport.py    # Graphviz DOT export
│   ├── metrics.py      # Metrics dataclass, table/CSV/JSON output
│   ├── main.py         # CLI entry point
│   └── __main__.py     # Enables `python -m dagopt`
├── tests/
│   ├── cases/          # Hand-crafted .tac input files (T01–T07)
│   └── test_*.py       # Pytest test modules
├── docs/
│   └── DECISIONS.md    # Design decisions and assumptions
├── pyproject.toml
└── README.md
```

---

## Optimization Pipeline

```
Input .tac file
      |
      v
  parse_tac()            List[Instr]
      |
      v
  build_blocks()         List[BasicBlock]   (split at labels / jumps)
      |
      v  (per block)
  build_dag()            DAG
    |-- Constant folding       (simplify.py: 2+3 -> 5)
    |-- Algebraic identities   (x*1 -> x, x+0 -> x, x-x -> 0 ...)
    |-- Commutativity          (b+a and a+b share one node)
    `-- CSE via hash table     (duplicate expressions share nodes)
      |
      v
  get_live_nodes()       Set[int]   (liveness + terminator reads)
      |
      v
  CodeGenerator          List[Instr]
    |-- Topological schedule (Kahn's algorithm)
    `-- Cycle breaking via fresh temporaries
      |
      v
  Optimized TAC output
```

---

## Design Decisions

See [`docs/DECISIONS.md`](docs/DECISIONS.md) for assumptions made where the spec was silent.
