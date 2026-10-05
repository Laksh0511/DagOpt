import pytest
from dagopt.tac import parse_tac, Instr
from dagopt.blocks import BasicBlock
from dagopt.dag import build_dag
from dagopt.codegen import CodeGenerator, optimize_block

def test_optimize_block_simple():
    code = """a = 2
b = 3
c = a + b"""
    instrs = parse_tac(code)
    block = BasicBlock(1, instrs)
    opt_instrs = optimize_block(block, r'^t\d+$')
    assert len(opt_instrs) == 3
    # Check that it computes correctly
    from dagopt.interp import interpret_block
    env = interpret_block(opt_instrs, {})
    assert env == {'a': 2, 'b': 3, 'c': 5}

def test_dead_code_elimination():
    code = """a = 2
b = 3
c = a + b
d = a * b"""
    instrs = parse_tac(code)
    block = BasicBlock(1, instrs)
    # only 'c' is live out
    opt_instrs = optimize_block(block, r'^t\d+$', override_live={'c'})
    # a, b, c will be kept, d dropped
    assert len(opt_instrs) == 1
    from dagopt.interp import interpret_block
    env = interpret_block(opt_instrs, {})
    assert 'c' in env
    assert 'd' not in env

def test_cycle_breaking():
    code = """t1 = a
a = b
b = t1"""
    instrs = parse_tac(code)
    block = BasicBlock(1, instrs)
    opt_instrs = optimize_block(block, r'^t\d+$', override_live={'a', 'b'})
    
    from dagopt.interp import interpret_block
    env = interpret_block(opt_instrs, {'a': 10, 'b': 20})
    assert env['a'] == 20
    assert env['b'] == 10
