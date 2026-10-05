import pytest
from dagopt.tac import parse_tac, Instr
from dagopt.verify import verify_block, generate_random_block

def test_verify_block_identical():
    code = """a = 2
b = 3
c = a + b"""
    instrs = parse_tac(code)
    res = verify_block(instrs, instrs, {'a', 'b', 'c'}, trials=10)
    assert res.passed
    assert res.trials_run > 0

def test_verify_block_broken():
    code1 = "c = a + b"
    code2 = "c = a - b"
    instrs1 = parse_tac(code1)
    instrs2 = parse_tac(code2)
    res = verify_block(instrs1, instrs2, {'c'}, trials=20)
    assert not res.passed
    assert res.failure_info is not None

def test_generate_random_block():
    instrs = generate_random_block(42, length=(5, 5))
    assert len(instrs) == 5
    for i in instrs:
        assert i.kind == 'binary'
