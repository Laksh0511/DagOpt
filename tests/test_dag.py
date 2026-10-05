import pytest
from dagopt.tac import parse_tac
from dagopt.blocks import build_blocks
from dagopt.dag import build_dag, dag_summary

def get_block_instrs(path):
    with open(path, "r") as f:
        code = f.read()
    blocks = build_blocks(parse_tac(code))
    return blocks[0].instrs

def test_dag_t01():
    instrs = get_block_instrs("tests/cases/T01.tac")
    dag = build_dag(instrs)
    
    # 4 leaves (b, c, a, d) ... wait.
    # a = b + c   (leaves b, c, op +)
    # b = a - d   (leaf d, op -)
    # c = b + c   (op + using new b, old c)
    # d = a - d   (op - using new a, old d) -> CSE!
    # Let's count nodes:
    # leaf b, leaf c => + (a)
    # leaf d => - (b)
    # new + (c)
    # cse - (d)
    # Leaves: b_0, c_0, d_0
    # Ops: + (n_b, n_c), - (n_a, n_d), + (n_b_new, n_c)
    # The last is a CSE hit: dag.table[('-', n_a, n_d)] exists
    assert dag.cse_hits == 1
    # Nodes:
    # n0: var b [b] initially, later loses b, but wait, b is assigned.
    # Actually b_0 has no labels at the end because b is reassigned.
    # Total nodes:
    # 0: var b
    # 1: var c
    # 2: + (0, 1) -> a
    # 3: var d [d] initially, later loses d
    # 4: - (2, 3) -> b, d
    # 5: + (4, 1) -> c
    # Let's verify lengths
    assert len(dag.nodes) == 6

def test_dag_t02():
    instrs = get_block_instrs("tests/cases/T02.tac")
    dag = build_dag(instrs)
    
    # t1 = a * b
    # t2 = a * b (CSE)
    # x = t1 + t2
    
    assert dag.cse_hits == 1
    assert len(dag.nodes) == 4 # var a, var b, *, +

def test_dag_t07():
    instrs = get_block_instrs("tests/cases/T07.tac")
    dag = build_dag(instrs)
    
    # a = b + c
    # b = 5
    # d = b + c (b is now 5, so no CSE with earlier b + c)
    
    assert dag.cse_hits == 0
    # Nodes: var b, var c, +, const 5, +
    assert len(dag.nodes) == 5
