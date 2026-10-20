# Branching and Control-Flow Example in TAC
# Demonstrates basic block partitioning, conditional & unconditional jumps,
# label leaders, and local DAG optimization within multi-block control flows.

# Block 0: Initialization (with constant folding and algebraic reduction)
i = 0
sum = 0
step = 1 + 0
limit = 5 * 2

# Block 1: Loop Header / Condition
LOOP:
if i >= limit goto EXIT

# Block 2: Loop Body (with local CSE & algebraic simplification)
t1 = step * 1
sum = sum + t1
t2 = step * 1
i = i + t2
goto LOOP

# Block 3: Loop Exit
EXIT:
res = sum + 0
