import pytest
from dagopt.tac import parse_tac, Instr
from dagopt.blocks import BasicBlock
from dagopt.dag import build_dag

def test_simplify_constant_folding():
    code = """a = 2
b = 3
c = a + b
d = c * 5
e = d - 10
f = e / 5
g = f % 2
h = -a"""
    instrs = parse_tac(code)
    dag = build_dag(instrs)
    # Check if a, b, c, d, e, f, g, h are all pointing to constants
    def assert_const(var, val):
        n = dag.nodes[dag.cur[var]]
        assert n.op == 'const'
        assert n.value == val
        
    assert_const('a', 2)
    assert_const('b', 3)
    assert_const('c', 5)
    assert_const('d', 25)
    assert_const('e', 15)
    assert_const('f', 3)
    assert_const('g', 1)
    assert_const('h', -2)

def test_simplify_algebraic_identities():
    code = """a = 5
b = x + 0
c = 0 + x
d = x * 1
e = 1 * x
f = x * 0
g = 0 * x
h = x - 0
i = x - x
j = x / 1
k = x / x"""
    instrs = parse_tac(code)
    dag = build_dag(instrs)
    
    n_x = dag.nodes[dag.cur['x']]
    
    # b, c, d, e, h, j should be the exact same node as x
    for var in ['b', 'c', 'd', 'e', 'h', 'j']:
        assert dag.cur[var] == dag.cur['x']
        
    # f, g, i should be constant 0
    for var in ['f', 'g', 'i']:
        n = dag.nodes[dag.cur[var]]
        assert n.op == 'const'
        assert n.value == 0
        
    # k should be constant 1
    n = dag.nodes[dag.cur['k']]
    assert n.op == 'const'
    assert n.value == 1

def test_simplify_no_div_zero():
    code = """a = 5
b = 0
c = a / b
d = a % b"""
    instrs = parse_tac(code)
    dag = build_dag(instrs)
    
    # c and d should NOT be constants, they should be binary nodes
    n_c = dag.nodes[dag.cur['c']]
    assert n_c.op == '/'
    n_d = dag.nodes[dag.cur['d']]
    assert n_d.op == '%'
