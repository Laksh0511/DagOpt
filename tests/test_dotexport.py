import pytest
from dagopt.tac import parse_tac, Instr
from dagopt.blocks import BasicBlock
from dagopt.dag import build_dag
from dagopt.dotexport import export_dot

def test_export_dot():
    code = """a = 2
b = 3
c = a + b
d = a * b"""
    instrs = parse_tac(code)
    dag = build_dag(instrs)
    # let's assume a, b, c are live, d is dead
    live = {dag.cur['a'], dag.cur['b'], dag.cur['c'], dag.leaf_const[2], dag.leaf_const[3]}
    dot = export_dot(dag, live)
    
    assert "digraph DAG {" in dot
    assert "rankdir=BT;" in dot
    assert "ordering=out;" in dot
    
    # Check that node d is marked dead
    # Node d should have a dashed style
    n_d = dag.cur['d']
    assert f'n{n_d} [' in dot
    assert 'dashed' in dot
