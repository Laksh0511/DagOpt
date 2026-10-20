# Testing Architecture & Verification Guide

## 1. Overview & Testing Philosophy

In compiler optimization, testing must answer two separate questions:
1. **Structural Correctness:** Does each compiler phase (lexing, basic block partitioning, DAG construction, constant folding, dead-code removal, and code generation) function according to specification?
2. **Semantic Soundness:** Does the optimized program compute the exact same output values as the unoptimized program for any arbitrary input?

To achieve this, **DAGOpt** implements a two-tier testing architecture:
- **Tier 1: Pytest Test Suite** (Unit & Integration tests across all modules).
- **Tier 2: Differential Soundness Fuzzer** (Concrete abstract interpretation across randomized input vectors).

---

## 2. Tier 1: Pytest Regression & Integration Suite

### 2.1 Configuration ([`pyproject.toml`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/pyproject.toml))
Pytest is integrated directly into the project configuration:

```toml
[project.optional-dependencies]
test = [
    "pytest",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

When invoked via `pytest` or `python -m pytest -v`, pytest automatically discovers test files matching `test_*.py` under [`tests/`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests) and runs every function prefixed with `def test_*():`.

### 2.2 Test Module Breakdown (34 Passing Tests)

| Test Module | Coverage Scope | Key Invariants Tested |
|---|---|---|
| [`tests/test_tac.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_tac.py) | TAC Parser & Lexer | Syntax validation, tokenization of copies, unaries, binaries, labels, jumps (`goto`), and conditionals (`if ... goto`). Guards against silent divide-by-zero crashes (`safe_div`). |
| [`tests/test_blocks.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_blocks.py) | Control Flow & Basic Blocks | Dragon Book leader detection: program start, branch targets, and instructions following branches. Correct block partition and successor linkage. |
| [`tests/test_dag.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_dag.py) | Graph Construction | Value numbering deduplication, dynamic label rebinding, and commutativity canonicalization (`x + y` vs `y + x`). |
| [`tests/test_simplify.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_simplify.py) | AST Simplification Rules | Constant folding cascades, algebraic identities (additive/multiplicative identities, zero annihilation, double negation), and division-by-zero preservation. |
| [`tests/test_codegen.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_codegen.py) | Code Generation | Topological instruction scheduling, dead node pruning, and Write-After-Read (WAR) cycle breaking via temporary allocation (`_n1`). |
| [`tests/test_interp.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_interp.py) | Concrete TAC Interpreter | Abstract execution of instructions in variable environments, undefined variable detection, and read-before-write analysis. |
| [`tests/test_verify.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_verify.py) | Verifier Self-Validation | Confirms that the differential verifier passes equivalent blocks, but catches intentional semantic mismatches (`a + b` vs `a - b`). |
| [`tests/test_dotexport.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_dotexport.py) | Graphviz Export | Validates DOT formatting and visualization attributes. |
| [`tests/test_metrics.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_metrics.py) | Metrics Engine | Validates aligned terminal table rendering and metric calculations. |
| [`tests/test_e2e.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/tests/test_e2e.py) | End-to-End Batch Pipeline | Dynamically collects all benchmark files in `tests/cases/*.tac` (T01–T07) and synthetic programs, asserting seamless optimization across multi-block flows. |

---

## 3. Tier 2: Differential Soundness Verifier & Abstract Interpreter

Passing unit tests does not mathematically guarantee that an optimized block behaves identically to the original code for all input combinations. **DAGOpt** solves this using **Differential Fuzzing** ([`dagopt/verify.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/verify.py)) paired with a concrete interpreter ([`dagopt/interp.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/interp.py)).

### 3.1 Verification Architecture

```
                       ┌─────────────────────────┐
                       │  Original TAC Block     │ ──┐
                       └─────────────────────────┘   │
  Random Inputs                                      ├──► Compare Outputs on Live-Out Variables
  (e.g., b=4, c=-1)                                  │    (orig_env[var] == opt_env[var])
                       ┌─────────────────────────┐   │
                       │  Optimized TAC Block    │ ──┘
                       └─────────────────────────┘
```

### 3.2 Verification Algorithm
1. **Input Variable Detection (`collect_reads_before_writes`):**
   Scans the unoptimized block to identify all variables read before being written.
2. **Biased Random Generation:**
   For $N$ trials (e.g. 100), generates input environments. Critically, it biases 30% of inputs toward edge values (`0`, `1`, `-1`), and the remainder across `[-20, 20]` to stress-test algebraic identity rules and zero conditions.
3. **Dual Interpretation:**
   The concrete interpreter runs the original block to produce `orig_env` and the optimized block to produce `opt_env`.
   - If the original code encounters division by zero, the trial is skipped.
   - If the optimized code faults when the original did not, verification fails immediately.
4. **State Equivalence Check:**
   Ensures `orig_env[var] == opt_env[var]` for all **live-out** variables (variables read by subsequent blocks or exits). Also checks condition operands in block branch terminators.

---

## 4. Control Flow & Branching Support ([`examples/branching.tac`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/examples/branching.tac))

**DAGOpt** supports complete control flow graphs with conditional and unconditional branches.

### Example Case:
```text
# Block 0: Initialization
i = 0
sum = 0
step = 1 + 0
limit = 5 * 2

# Block 1: Loop Header / Condition
LOOP:
if i >= limit goto EXIT

# Block 2: Loop Body
t1 = step * 1
sum = sum + t1
t2 = step * 1
i = i + t2
goto LOOP

# Block 3: Loop Exit
EXIT:
res = sum + 0
```

### Leader Analysis & Partitioning:
1. **Rule 1 (First line):** `i = 0` starts Block 0.
2. **Rule 2 (Target of a branch):** `LOOP:` is targeted by `goto LOOP`, starting Block 1.
3. **Rule 3 (Following a branch):** `t1 = step * 1` follows `if i >= limit goto EXIT`, starting Block 2.
4. **Rule 2 & 3:** `EXIT:` follows `goto LOOP` and is targeted by the conditional jump, starting Block 3.

### Running Multi-Block Optimization:
```powershell
python -m dagopt examples/branching.tac --metrics
```
**Results across 4 basic blocks:**
- **Block 0:** 2 arithmetic operations folded into compile-time constants (`step = 1`, `limit = 10`).
- **Block 1:** Evaluates loop branch terminator `if i >= limit goto EXIT`.
- **Block 2:** Applies algebraic identity simplifications (`step * 1 -> step`), resolves Write-After-Read hazards using temporaries (`_n1`, `_n2`), and emits `goto LOOP`.
- **Block 3:** Eliminates additive identity (`sum + 0 -> sum`).
- **All 4 blocks pass semantic equivalence verification (`Verify: True`).**

---

## 5. How to Run the Tests

Activate the virtual environment and execute pytest:

```powershell
# Activate environment
.\.venv\Scripts\activate

# Run full test suite with verbose output
python -m pytest -v

# Run a specific test module
python -m pytest tests/test_simplify.py -v

# Run the live 7-phase step-by-step diagnostic walkthrough
python examples/verify_demo.py tests/cases/T01.tac
```
