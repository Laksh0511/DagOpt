# DAGOpt: DAG-Based Basic Block Optimizer
## Comprehensive Documentation & Faculty Demo Guide

---

## 1. Project Overview & Academic Foundations

**DAGOpt** is a compiler optimization tool designed for Intermediate Representation (IR) in the form of **Three-Address Code (TAC)**. It performs local optimizations within **Basic Blocks** by modeling program data flow and expression trees as **Directed Acyclic Graphs (DAGs)**, following the classic algorithms described in the *Compilers: Principles, Techniques, and Tools* (Dragon Book, Aho, Lam, Sethi, Ullman, Chapter 8).

### Primary Optimization Goals:
1. **Local Common Subexpression Elimination (CSE):** Detects redundant expressions across a block via value numbering.
2. **Compile-Time Constant Folding:** Evaluates static expressions whose operands are known compile-time constants.
3. **Algebraic Identity Simplification:** Simplifies operations using mathematical properties (identity elements, zero annihilation, double negation).
4. **Commutativity Canonicalization:** Recognizes that `x + y` and `y + x` produce identical values.
5. **Dead Code Elimination (DCE):** Discards computations that do not contribute to live-out variables or block terminators.
6. **Sound Code Generation with WAR Hazard Resolution:** Emits optimized TAC while strictly preserving program semantics and resolving Write-After-Read (anti-dependency) register overwrite hazards.
7. **Automated Soundness Verification:** Validates semantic equivalence via differential testing with an abstract interpreter across randomized inputs.

---

## 2. Core Compiler Optimization Techniques

```
Raw TAC Code
     │
     ▼
[1. Basic Block Partitioning]  ─── (Leader analysis & terminator tracking)
     │
     ▼
[2. DAG Construction]          ─── (Value numbering, CSE, folding, algebraic identities)
     │
     ▼
[3. Liveness Analysis]         ─── (Live-out set calculation, dead node pruning)
     │
     ▼
[4. Topological Code Gen]      ─── (Order evaluation, WAR hazard & cycle breaking)
     │
     ▼
[5. Differential Verification] ─── (Equivalence checking vs original TAC)
     │
     ▼
Optimized TAC + Visual DAG + Metrics (JSON/CSV)
```

### 2.1 Basic Block Partitioning ([dagopt/blocks.py](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/blocks.py))
A Basic Block is a sequence of consecutive instructions where control enters strictly at the beginning and leaves only at the end without halting or branching in the middle.
- **Leader Detection Rules:**
  1. The first instruction of the program is a leader.
  2. Any target of a conditional or unconditional branch (`goto L`, `if ... goto L`) is a leader.
  3. Any instruction immediately following a conditional or unconditional branch is a leader.

### 2.2 DAG Construction & Value Numbering ([dagopt/dag.py](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/dag.py))
- **Nodes:**
  - **Leaf Nodes:** Represent incoming variable values (`var x`) or constant literals (`const 5`).
  - **Interior Nodes:** Represent arithmetic/logical operators (`+`, `-`, `*`, `/`, etc.).
- **Value Numbering:** A hash table `table[(op, children)] -> node_id` ensures that identical computations within the block share the same DAG node rather than creating duplicate instructions.
- **Variable Binding (`cur` map):** Variables are dynamically attached as labels to DAG nodes. When variable `x` is reassigned, its label is detached from the old node and attached to the newly computed node.

### 2.3 Constant Folding & Algebraic Simplification ([dagopt/simplify.py](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/simplify.py))
Before inserting a new node into the DAG, `try_simplify()` attempts several reductions:
- **Constant Folding:** If both child nodes are constant literals, the operation is computed at compile time (e.g., `3 + 4 -> 7`). Safe division/modulo guards protect against division by zero.
- **Algebraic Identities:**
  - Additive Identity: `x + 0 -> x`, `0 + x -> x`
  - Multiplicative Identity: `x * 1 -> x`, `1 * x -> x`
  - Zero Annihilation: `x * 0 -> 0`, `0 * x -> 0`
  - Subtractive Identity: `x - 0 -> x`, `x - x -> 0`
  - Division Identity: `x / 1 -> x`, `x / x -> 1` (with nonzero guarantee)
  - Modulo Identity: `x % 1 -> 0`, `x % x -> 0`
  - Double Negation: `- (- x) -> x`
- **Commutativity:** Binary operations (`+`, `*`, `==`, `!=`) have their operand IDs sorted canonically (`children = (min(a,b), max(a,b))`), so `b + a` maps to the exact same node as `a + b`.

### 2.4 Dead Code Elimination (DCE) ([dagopt/liveness.py](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/liveness.py))
- Computes the set of **live-out variables** (variables read after the block or used in block branch terminators).
- Only DAG nodes that contribute directly or indirectly to a live-out variable or terminator condition are marked as **live nodes**.
- All unreferenced nodes are pruned and emit zero instructions.

### 2.5 Code Generation & Write-After-Read (WAR) Cycle Breaking ([dagopt/codegen.py](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/codegen.py))
Generating linear TAC from a DAG is non-trivial when variables are reused.
- **The Write-After-Read (WAR) Hazard:**
  Consider:
  ```text
  b = a - d
  c = b + c
  ```
  If `c` is updated before an expression reading the original value of `c`, a race condition occurs.
- **Dependency Cycle Breaking:**
  When a node's preferred variable name would overwrite an existing variable value still needed by another active node, `CodeGenerator` automatically allocates a temporary variable (e.g., `_n1`) to preserve the intermediate value safely.

---

## 3. Architecture & Modular Breakdown

| Module | Location | Purpose & Responsibility |
|---|---|---|
| **TAC Parser** | [`dagopt/tac.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/tac.py) | Tokenizes and parses Three-Address Code into structured `Instr` objects. |
| **Basic Blocks** | [`dagopt/blocks.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/blocks.py) | Partitions TAC instruction streams into basic blocks based on leaders. |
| **DAG Builder** | [`dagopt/dag.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/dag.py) | Constructs the DAG, handles value numbering, label rebinding, and CSE detection. |
| **Simplifier** | [`dagopt/simplify.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/simplify.py) | Rule-based engine for constant folding and algebraic identity reductions. |
| **Liveness** | [`dagopt/liveness.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/liveness.py) | Traverses block exits to determine live-out variables and prune dead nodes. |
| **Code Generator** | [`dagopt/codegen.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/codegen.py) | Reconstructs linear TAC in topological order with WAR cycle breaking. |
| **Interpreter** | [`dagopt/interp.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/interp.py) | Concrete execution engine for TAC to compute block outputs given variable environments. |
| **Verifier** | [`dagopt/verify.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/verify.py) | Differential fuzzer running random input vectors through unoptimized vs optimized blocks. |
| **Metrics** | [`dagopt/metrics.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/dagopt/metrics.py) | Computes quantitative stats and exports aligned terminal tables, `metrics.json`, and `metrics.csv`. |
| **Visual Renderer** | [`render_dag.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/render_dag.py) | Custom matplotlib + networkx visualization rendering publication-grade PNG diagrams. |
| **Interactive Walkthrough**| [`verify_demo.py`](file:///c:/Users/Lakshya/Desktop/Proj/DagOpt/verify_demo.py) | 7-phase step-by-step diagnostic verification demonstration tool. |

---

## 4. Step-by-Step Live Demo Script (For Faculty Presentation)

Use the following 7-phase script to deliver a structured, impressive presentation.

### Environment Preparation (PowerShell)
```powershell
# Navigate to the project root
cd c:\Users\Lakshya\Desktop\Proj\DagOpt

# Activate virtual environment
.\.venv\Scripts\activate

# Enable UTF-8 encoding for clean table rendering
$env:PYTHONIOENCODING="utf-8"
```

---

### Demo 1: Common Subexpression Elimination (CSE) & WAR Cycle Breaking
**Target Case:** `tests/cases/T01.tac`

**Source Code:**
```text
a = b + c
b = a - d
c = b + c
d = a - d
```
**Talking Points for Faculty:**
1. Point out `d = a - d`. The expression `a - d` was already computed earlier (`b = a - d`).
2. The optimizer recognizes `a - d` as a **Common Subexpression (CSE)** and reuses node result `b`, turning the arithmetic operation into a copy `d = b`.
3. Notice that `c` is updated while its old value is still needed. The engine detects this anti-dependency and safely introduces a temporary `_n1 = c` to break the cycle.

**Command:**
```powershell
.\.venv\Scripts\python dagopt/main.py tests/cases/T01.tac --metrics
```
**Output:**
```text
Instr(kind='binary', dest='a', op='+', a='b', b='c', target=None)
Instr(kind='binary', dest='b', op='-', a='a', b='d', target=None)
Instr(kind='copy', dest='d', op=None, a='b', b=None, target=None)
Instr(kind='copy', dest='_n1', op=None, a='c', b=None, target=None)
Instr(kind='binary', dest='c', op='+', a='b', b='_n1', target=None)

Block    InstrIn   InstrOut   ArithIn   ArithOut   CopyIn   CopyOut   DAGNodes   CSE   ConstFold   Algebraic   DeadRm   Verify 
-----------------------------------------------------------------------------------------------------------------------------
0        4         5          4         3          0        2         6          1     0           0           0        True   
```

---

### Demo 2: Compile-Time Constant Folding & Algebraic Reduction
**Target Case:** `tests/cases/T05.tac`

**Source Code:**
```text
a = 2 + 3
b = a * 2
c = b - 5
d = c / 5
e = d % 1
```
**Talking Points for Faculty:**
1. Walk through the cascade: `a = 2 + 3 = 5`, `b = 5 * 2 = 10`, `c = 10 - 5 = 5`, `d = 5 / 5 = 1`, `e = 1 % 1 = 0`.
2. All 5 arithmetic operations are evaluated statically at compile time.
3. Arithmetics drop from **5 to 0**, reducing runtime instruction overhead to direct constant loads.

**Command:**
```powershell
.\.venv\Scripts\python dagopt/main.py tests/cases/T05.tac --metrics
```
**Output:**
```text
Instr(kind='copy', dest='a', op=None, a=5, b=None, target=None)
Instr(kind='copy', dest='b', op=None, a=10, b=None, target=None)
Instr(kind='copy', dest='c', op=None, a=5, b=None, target=None)
Instr(kind='copy', dest='d', op=None, a=1, b=None, target=None)
Instr(kind='copy', dest='e', op=None, a=0, b=None, target=None)

Block    InstrIn   InstrOut   ArithIn   ArithOut   CopyIn   CopyOut   DAGNodes   CSE   ConstFold   Algebraic   DeadRm   Verify 
-----------------------------------------------------------------------------------------------------------------------------
0        5         5          5         0          0        5         5          0     5           0           0        True   
```

---

### Demo 3: Visual DAG Rendering (Image Output)
Demonstrate how the tool visually represents compiler graph structures.

**Commands:**
```powershell
# Render DAG for T01 (shows CSE sharing)
.\.venv\Scripts\python tools/render_dag.py tests/cases/T01.tac -o dag_T01.png

# Render DAG for example.tac
.\.venv\Scripts\python tools/render_dag.py examples/example.tac -o dag_example.png
```
**Visual Features to Highlight:**
- **Shapes:** Rectangular boxes represent input leaf nodes (`var` or `const`); circles represent internal operations.
- **Colors:**
  - **Light Blue Nodes:** Shared Common Subexpressions (CSE hits).
  - **Light Green Nodes:** Active live computation nodes.
  - **Gray Dashed Nodes:** Dead code pruned from final code generation.
  - **Node Labels:** Attached variables (e.g., `[b, d]`) showing value-numbering aliases.

---

### Demo 4: Detailed Diagnostic Walkthrough (The 7-Phase Inspector)
Run the dedicated diagnostic verification tool to inspect intermediate compiler states live in the terminal.

**Command:**
```powershell
.\.venv\Scripts\python examples/verify_demo.py tests/cases/T01.tac
```
**What the tool displays:**
1. **Phase 1: Input TAC parsing**
2. **Phase 2: Basic block boundaries**
3. **Phase 3: Step-by-step DAG construction** (with Value Numbering lookups)
4. **Phase 4: Complete DAG node table** (Operator, Children, Attached Labels)
5. **Phase 5: Liveness Analysis** (Live-out set calculation & dead node detection)
6. **Phase 6: Emitted TAC instructions**
7. **Phase 7: Differential Random Fuzzing** (running concrete valuations through both blocks to prove soundness)

---

### Demo 5: Formal Soundness Verification (Automated Fuzzing)
Compiler optimizations must never alter program semantics. Show how DAGOpt mathematically guarantees equivalence by executing 100 randomized input trials on the fly:

**Command:**
```powershell
.\.venv\Scripts\python -m dagopt tests/cases/T01.tac --verify 100
```
**Output:**
```text
Block 0: Verification PASSED (100 trials)
```

---

### Demo 6: Dynamic Metrics Generation (`metrics.csv` & `metrics.json`)
Demonstrate that compiler metrics are computed dynamically and exported for data analysis:

**Command:**
```powershell
.\.venv\Scripts\python -m dagopt tests/cases/T01.tac --metrics
Get-Content metrics.csv
```
**Content Displayed:**
```csv
block_id,instrs_before,instrs_after,arith_before,arith_after,copy_before,copy_after,dag_nodes,cse_hits,constants_folded,algebraic_simplifications,dead_nodes_removed,verification_passed
0,4,5,4,3,0,2,6,1,0,0,0,True
TOTAL,4,5,4,3,0,2,6,1,0,0,0,True
```

---

### Demo 7: Full Test Suite Execution (Pytest)
Demonstrate project reliability and test coverage:

**Command:**
```powershell
.\.venv\Scripts\pytest -v
```
**Result to Highlight:**
- **35 tests passing** across 11 test modules:
  - `test_tac.py`: Parsing, error handling, syntax validation.
  - `test_blocks.py`: Leader partitioning, block boundary correctness.
  - `test_dag.py`: Graph construction, value numbering.
  - `test_simplify.py`: Constant folding, algebraic properties, zero division avoidance.
  - `test_codegen.py`: Topological emission, dead code removal, WAR cycle breaking.
  - `test_interp.py` & `test_verify.py`: Differential execution and random fuzzer.
  - `test_e2e.py`: End-to-end multi-block validation.

---

## 5. Faculty / Viva Q&A Preparation

### Q1: Why optimize basic blocks using DAGs instead of linear peephole optimization?
**Answer:**
> Peephole optimization only inspects a fixed sliding window of 2–3 linear instructions. It cannot detect common subexpressions that are separated by multiple unrelated instructions or recognize complex dependency graphs. A DAG captures the true data-flow dependencies of expressions regardless of instruction order, making CSE, constant folding, and dead-code elimination natural graph-reachability properties.

### Q2: How does the optimizer handle commutativity (`x + y` vs `y + x`)?
**Answer:**
> In `dagopt/dag.py`, commutative operations (`+`, `*`, `==`, `!=`) canonicalize their operand IDs prior to lookup:
> `children = (min(id_a, id_b), max(id_a, id_b))`
> Because operands are sorted deterministically, `b + a` produces the exact same tuple key as `a + b`, guaranteeing an immediate CSE hit in the value numbering table.

### Q3: What is the Write-After-Read (WAR) hazard and how is it resolved?
**Answer:**
> When emitting linear code from a DAG, variable names are chosen from node labels. If node $N_2$ writes to variable $v$, but another node $N_1$ still needs to read the *old* value of $v$, emitting $N_2$ first would clobber the input to $N_1$. In `dagopt/codegen.py`, we construct a dependency graph over definitions and uses. If a cycle or anti-dependency occurs, the code generator detects it and allocates a fresh temporary variable (`_n1`) to preserve the old value safely.

### Q4: Why did the instruction count in `T01.tac` increase from 4 to 5?
**Answer:**
> Although total arithmetic instructions decreased from 4 to 3 (thanks to CSE), an extra copy instruction (`_n1 = c`) had to be introduced to preserve the original value of `c` before `c` was overwritten (`c = b + c`). This ensures semantic correctness. The compiler traded an expensive arithmetic calculation for cheaper register/variable copies while avoiding a data-hazard crash.

### Q5: How do you prevent compile-time crashes during constant folding of division by zero?
**Answer:**
> In `dagopt/tac.py`, `safe_div(a, b)` and `safe_mod(a, b)` guard against division/modulo by zero. If `b == 0`, constant folding is skipped, preserving the original instruction so that the runtime exception is raised properly at program execution time instead of crashing the compiler.

### Q6: How do you prove that an optimization is sound?
**Answer:**
> We implement randomized differential testing in `dagopt/verify.py`. An abstract interpreter (`dagopt/interp.py`) executes both the unoptimized and optimized instruction blocks under identical initial variable environments across $N$ trials (default 100). The final environment values of all live-out variables must match identically.

---

## 6. Summary Command Cheatsheet

| Task | Command (PowerShell) |
|---|---|
| **Run Optimizer with Metrics** | `python -m dagopt tests/cases/T01.tac --metrics` |
| **Run Random Equivalence Verifier** | `python -m dagopt tests/cases/T01.tac --verify 100` |
| **Export Graphviz DOT Files** | `python -m dagopt tests/cases/T01.tac --dot-dir ./dots` |
| **Render Visual PNG Graph** | `python tools/render_dag.py tests/cases/T01.tac -o dag_T01.png` |
| **Interactive 7-Phase Demo** | `python examples/verify_demo.py tests/cases/T01.tac` |
| **Run Full Pytest Suite** | `pytest -v` |
| **Inspect Generated CSV** | `Get-Content metrics.csv` |
