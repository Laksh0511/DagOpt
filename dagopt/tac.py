"""
TAC Data Structures and Parser.
"""
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Instr:
    kind: str            # 'copy','unary','binary','label','goto','cond'
    dest: str | None     # assigned variable (copy/unary/binary)
    op: str | None       # operator or relop
    a: str | int | None  # first operand (variable name or int)
    b: str | int | None  # second operand (binary/cond)
    target: str | None   # label name (label/goto/cond)

class TacSyntaxError(Exception):
    def __init__(self, line_no: int, message: str):
        super().__init__(f"Line {line_no}: {message}")
        self.line_no = line_no
        self.message = message

def safe_div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return int(a / b)  # C-style truncation towards zero

def safe_mod(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("modulo by zero")
    # C-style modulo: takes the sign of the dividend
    res = abs(a) % abs(b)
    return res if a >= 0 else -res

def is_temp(name: str, regex: str = r"^(t[0-9]+|_n[0-9]+)$") -> bool:
    return bool(re.match(regex, name))

def _parse_operand(op: str) -> str | int:
    try:
        return int(op)
    except ValueError:
        return op

def parse_tac(text: str) -> list[Instr]:
    instructions = []
    lines = text.splitlines()
    
    # regexes
    ident = r"[A-Za-z_][A-Za-z0-9_]*"
    operand = rf"({ident}|-?\d+)"
    op_bin = r"(\+|\-|\*|\/|\%)"
    relop = r"(<|<=|>|>=|==|!=)"
    
    # x = y
    copy_re = re.compile(rf"^({ident})\s*=\s*{operand}$")
    # x = - y
    unary_re = re.compile(rf"^({ident})\s*=\s*-\s*{operand}$")
    # x = y op z
    binary_re = re.compile(rf"^({ident})\s*=\s*{operand}\s*{op_bin}\s*{operand}$")
    # L1:
    label_re = re.compile(rf"^({ident}):$")
    # goto L1
    goto_re = re.compile(rf"^goto\s+({ident})$")
    # if y relop z goto L1
    cond_re = re.compile(rf"^if\s+{operand}\s*{relop}\s*{operand}\s+goto\s+({ident})$")

    for i, line in enumerate(lines, 1):
        # strip comments and whitespace
        line = line.split('#')[0].strip()
        if not line:
            continue
            
        m = copy_re.match(line)
        if m:
            instructions.append(Instr('copy', m.group(1), None, _parse_operand(m.group(2)), None, None))
            continue
            
        m = unary_re.match(line)
        if m:
            instructions.append(Instr('unary', m.group(1), 'neg', _parse_operand(m.group(2)), None, None))
            continue
            
        m = binary_re.match(line)
        if m:
            instructions.append(Instr('binary', m.group(1), m.group(3), _parse_operand(m.group(2)), _parse_operand(m.group(4)), None))
            continue
            
        m = label_re.match(line)
        if m:
            instructions.append(Instr('label', None, None, None, None, m.group(1)))
            continue
            
        m = goto_re.match(line)
        if m:
            instructions.append(Instr('goto', None, None, None, None, m.group(1)))
            continue
            
        m = cond_re.match(line)
        if m:
            instructions.append(Instr('cond', None, m.group(2), _parse_operand(m.group(1)), _parse_operand(m.group(3)), m.group(4)))
            continue
            
        raise TacSyntaxError(i, f"Invalid TAC syntax: '{line}'")

    return instructions

def format_instr(instr: Instr) -> str:
    if instr.kind == 'copy':
        return f"{instr.dest} = {instr.a}"
    elif instr.kind == 'unary':
        return f"{instr.dest} = - {instr.a}"
    elif instr.kind == 'binary':
        return f"{instr.dest} = {instr.a} {instr.op} {instr.b}"
    elif instr.kind == 'label':
        return f"{instr.target}:"
    elif instr.kind == 'goto':
        return f"goto {instr.target}"
    elif instr.kind == 'cond':
        return f"if {instr.a} {instr.op} {instr.b} goto {instr.target}"
    raise ValueError(f"Unknown instruction kind: {instr.kind}")
