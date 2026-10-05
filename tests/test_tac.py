import pytest
from dagopt.tac import Instr, TacSyntaxError, safe_div, safe_mod, parse_tac, format_instr, is_temp

def test_safe_div():
    assert safe_div(7, 2) == 3
    assert safe_div(-7, 2) == -3
    assert safe_div(7, -2) == -3
    assert safe_div(-7, -2) == 3
    with pytest.raises(ZeroDivisionError):
        safe_div(5, 0)

def test_safe_mod():
    assert safe_mod(7, 2) == 1
    assert safe_mod(-7, 2) == -1
    assert safe_mod(7, -2) == 1
    assert safe_mod(-7, -2) == -1
    with pytest.raises(ZeroDivisionError):
        safe_mod(5, 0)

def test_is_temp():
    assert is_temp("t1")
    assert is_temp("t42")
    assert is_temp("_n5")
    assert not is_temp("x")
    assert not is_temp("t")
    assert not is_temp("_n")

def test_parse_tac_copy():
    code = "x = y"
    instrs = parse_tac(code)
    assert len(instrs) == 1
    assert instrs[0] == Instr('copy', 'x', None, 'y', None, None)
    
    code2 = "x = 42"
    instrs2 = parse_tac(code2)
    assert instrs2[0] == Instr('copy', 'x', None, 42, None, None)

def test_parse_tac_unary():
    code = "x = - y"
    instrs = parse_tac(code)
    assert len(instrs) == 1
    assert instrs[0] == Instr('unary', 'x', 'neg', 'y', None, None)

def test_parse_tac_binary():
    code = "x = y + z"
    instrs = parse_tac(code)
    assert len(instrs) == 1
    assert instrs[0] == Instr('binary', 'x', '+', 'y', 'z', None)

    code2 = "x = -5 * a"
    instrs2 = parse_tac(code2)
    assert instrs2[0] == Instr('binary', 'x', '*', -5, 'a', None)

def test_parse_tac_label():
    code = "L1:"
    instrs = parse_tac(code)
    assert len(instrs) == 1
    assert instrs[0] == Instr('label', None, None, None, None, 'L1')

def test_parse_tac_goto():
    code = "goto L1"
    instrs = parse_tac(code)
    assert len(instrs) == 1
    assert instrs[0] == Instr('goto', None, None, None, None, 'L1')

def test_parse_tac_cond():
    code = "if x < y goto L1"
    instrs = parse_tac(code)
    assert len(instrs) == 1
    assert instrs[0] == Instr('cond', None, '<', 'x', 'y', 'L1')

def test_parse_tac_comments_and_whitespace():
    code = """
    
    x = y   # comment
    L1:     # label comment
    
    """
    instrs = parse_tac(code)
    assert len(instrs) == 2
    assert instrs[0].kind == 'copy'
    assert instrs[1].kind == 'label'

def test_parse_tac_errors():
    invalid_cases = [
        ("x = y +", 1),
        ("if x << y goto L1", 1),
        ("x == y", 1),
        ("goto", 1),
        ("123 =", 1),
    ]
    for code, line_no in invalid_cases:
        with pytest.raises(TacSyntaxError) as excinfo:
            parse_tac(code)
        assert excinfo.value.line_no == line_no

def test_format_instr():
    code = """x = y
x = - y
x = y + z
L1:
goto L1
if x < y goto L1"""
    instrs = parse_tac(code)
    formatted = [format_instr(i) for i in instrs]
    assert "\n".join(formatted) == code
