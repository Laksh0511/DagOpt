import pytest
from dagopt.tac import parse_tac
from dagopt.blocks import build_blocks

def test_build_blocks_simple():
    code = """x = 1
y = 2
z = x + y"""
    instrs = parse_tac(code)
    blocks = build_blocks(instrs)
    
    assert len(blocks) == 1
    assert len(blocks[0].instrs) == 3
    assert blocks[0].terminator is None
    assert blocks[0].successors == []

def test_build_blocks_t12():
    code = """a = 1
L1:
b = 2
if a < b goto L2
c = 3
goto L1
L2:
d = 4"""
    instrs = parse_tac(code)
    blocks = build_blocks(instrs)
    
    assert len(blocks) == 4
    
    # Block 0: a = 1
    assert len(blocks[0].instrs) == 1
    assert blocks[0].terminator is None
    assert blocks[0].successors == [1]
    
    # Block 1: L1:, b = 2, if ... goto L2
    assert len(blocks[1].instrs) == 2
    assert blocks[1].terminator is not None
    assert blocks[1].terminator.kind == 'cond'
    assert set(blocks[1].successors) == {2, 3}
    
    # Block 2: c = 3, goto L1
    assert len(blocks[2].instrs) == 1
    assert blocks[2].terminator is not None
    assert blocks[2].terminator.kind == 'goto'
    assert blocks[2].successors == [1]
    
    # Block 3: L2:, d = 4
    assert len(blocks[3].instrs) == 2
    assert blocks[3].terminator is None
    assert blocks[3].successors == []

def test_build_blocks_edge_cases():
    # Jump to first line
    code1 = """L1:
x = 1
goto L1"""
    blocks1 = build_blocks(parse_tac(code1))
    assert len(blocks1) == 1
    assert blocks1[0].successors == [0]
    
    # Back-to-back labels
    code2 = """L1:
L2:
x = 1"""
    blocks2 = build_blocks(parse_tac(code2))
    assert len(blocks2) == 2
    assert len(blocks2[0].instrs) == 1
    assert len(blocks2[1].instrs) == 2
    
    # Trailing label
    code3 = """x = 1
L1:"""
    blocks3 = build_blocks(parse_tac(code3))
    assert len(blocks3) == 2
    assert len(blocks3[0].instrs) == 1
    assert len(blocks3[1].instrs) == 1
