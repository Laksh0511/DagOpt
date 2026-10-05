import pytest
from dagopt.tac import parse_tac
from dagopt.interp import interpret_block, collect_reads_before_writes, UndefinedVarError

def test_interpret_block_simple():
    code = """a = 2
b = 3
c = a + b"""
    instrs = parse_tac(code)
    env = interpret_block(instrs, {})
    assert env == {'a': 2, 'b': 3, 'c': 5}

def test_interpret_block_division():
    code = "c = a / b"
    instrs = parse_tac(code)
    env = interpret_block(instrs, {'a': -7, 'b': 2})
    assert env['c'] == -3
    
    with pytest.raises(ZeroDivisionError):
        interpret_block(instrs, {'a': 5, 'b': 0})

def test_interpret_block_undefined():
    code = "c = a + b"
    instrs = parse_tac(code)
    with pytest.raises(UndefinedVarError):
        interpret_block(instrs, {'a': 1})

def test_collect_reads_before_writes():
    code = """a = 2
c = a + b
b = 5
d = b + e"""
    instrs = parse_tac(code)
    reads = collect_reads_before_writes(instrs)
    # a is written before read, so not in reads
    # b is read in line 2 before written in line 3 -> 'b' in reads
    # e is read before written -> 'e' in reads
    assert reads == {'b', 'e'}
