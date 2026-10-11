# Assumptions and Decisions

This document records the design assumptions, architectural decisions, and trade-offs made where specifications were silent or flexible.

---

## 1. Intermediate Representation & Three-Address Code (TAC)

- **Instruction Categories:** TAC instructions are categorized into `copy` (`x = y`), `binary` (`x = y op z`), `unary` (`x = - y`), `label` (`L:`), `goto` (`goto L`), and `cond_branch` (`if a rel b goto L`).
- **Operands & Literals:** Operands are integer literals or identifiers conforming to `[A-Za-z_][A-Za-z0-9_]*`.
- **Comments and Whitespace:** Lines containing `#` strip comments; empty or comment-only lines are ignored during IR parsing.
- **Relational Operators:** Supported conditional relational operators include `<`, `<=`, `>`, `>=`, `==`, and `!=`.

---

## 2. Basic Block Partitioning

- **Leader Detection Rules:**
  1. The first instruction of the program is a leader.
  2. Any target of a conditional or unconditional branch is a leader.
  3. Any instruction immediately following a conditional or unconditional branch is a leader.
- **Block Terminators:** Branches (`goto`, `if ... goto`) are treated as block terminators and attached to `BasicBlock.terminator`. If a block does not end with a branch, control falls through to the next sequential block. Labels precede instructions and delimit block entry points.

---

## 3. DAG Representation & Value Numbering

- **Node Types:**
  - **Leaf Nodes:** Represent initial variable inputs (`op = "var"`) or compile-time literals (`op = "const"`).
  - **Interior Nodes:** Represent arithmetic/logical operators (`+`, `-`, `*`, `/`, `%`).
- **Dynamic Variable Binding (`cur` map):** Variables are dynamically attached as aliases/labels to DAG nodes. When a variable $x$ is reassigned in the basic block, its label is detached from its previous DAG node and attached to the newly computed node.
- **Value Numbering Key:** `(op, left_child_id, right_child_id)` ensures that identical computations in the block map to the same node, achieving local Common Subexpression Elimination (CSE).

---

## 4. Commutativity & Canonicalization

- **Commutative Operators:** `+`, `*`, `==`, `!=`.
- **Canonical Ordering:** Operands are sorted deterministically by DAG node ID:
  $$\text{children} = (\min(\text{id}_a, \text{id}_b), \max(\text{id}_a, \text{id}_b))$$
- **Effect:** Instructions like `c = a + b` followed by `d = b + a` naturally map to the exact same DAG node key without requiring special-case AST re-matching.

---

## 5. Constant Folding & Algebraic Simplifications

- **Division and Modulo Safety:** Division or modulo by zero is **not** folded at compile time; folding is skipped so runtime semantics and exception behaviors are preserved.
- **Identities Applied:**
  - Addition identity: $x + 0 \to x$, $0 + x \to x$
  - Subtraction identity: $x - 0 \to x$
  - Self subtraction: $x - x \to 0$
  - Multiplication identity: $x \times 1 \to x$, $1 \times x \to x$
  - Multiplication annihilation: $x \times 0 \to 0$, $0 \times x \to 0$
  - Division identity: $x / 1 \to x$
  - Self division: $x / x \to 1$ (if $x \neq 0$)
  - Double negation: $-(-x) \to x$
- **Simplification Priority:** Constant folding is evaluated first. If either operand is a runtime variable, algebraic reduction rules are evaluated before a new interior operator node is inserted into the DAG.

---

## 6. Liveness Analysis & Dead-Code Pruning

- **Live-Out Sets:**
  - Variables considered globally live-out are read by subsequent basic blocks or program exits.
  - A configurable regex (default `^_(t|n)\d+$`) identifies internal compiler temporaries; temporaries are not assumed live unless explicitly read downstream.
  - A CLI override `--live-out` allows explicit comma-separated specification of variable names for closed block testing.
- **Dead Node Removal:** Any DAG node with no live variable labels, no live descendants, and no references in the block terminator is marked dead and pruned before linear code generation.

---

## 7. Topological Code Generation & WAR Hazard Resolution

- **Emission Order:** Linear instructions are emitted in a valid topological ordering (operands computed before parent operations).
- **Write-After-Read (WAR) Anti-Dependency Handling:**
  - When emitting $x = y \text{ op } z$, if $x$ clobbers a variable name that is still needed as an input to a subsequent, not-yet-emitted node, a hazard exists.
  - If an anti-dependency cycle occurs, the code generator emits an intermediate assignment to a fresh temporary (`_n<id>`) to preserve the read value before it is overwritten.
- **Trade-off:** Instruction counts may occasionally increase (e.g. from 4 to 5 instructions) by inserting a cheap copy instruction to guarantee sound register reuse without semantic corruption.

---

## 8. Differential Soundness Verification

- **Random Input Fuzzing:**
  - Block equivalence is proved by executing unoptimized vs optimized code via an abstract TAC interpreter (`dagopt.interp.interpret_block`).
  - Inputs not initialized prior to first read are populated with pseudo-random integers.
  - Equivalence passes if and only if all variables in the `live_out` set have identical values at block exit across all trials ($N \ge 10$).
