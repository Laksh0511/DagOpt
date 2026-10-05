"""
TAC Interpreter.
"""
from typing import List, Dict, Set
from dagopt.tac import Instr, safe_div, safe_mod

class UndefinedVarError(Exception):
    pass

def collect_reads_before_writes(instrs: List[Instr]) -> Set[str]:
    reads = set()
    writes = set()
    
    def check_read(op):
        if isinstance(op, str) and op not in writes:
            reads.add(op)
            
    for instr in instrs:
        if instr.kind in ('copy', 'unary', 'binary'):
            check_read(instr.a)
            if instr.kind == 'binary':
                check_read(instr.b)
            if instr.dest:
                writes.add(instr.dest)
        elif instr.kind == 'cond':
            check_read(instr.a)
            check_read(instr.b)
    
    return reads

def interpret_block(instrs: List[Instr], env: Dict[str, int]) -> Dict[str, int]:
    current_env = dict(env)
    
    def get_val(op):
        if isinstance(op, int):
            return op
        if op not in current_env:
            raise UndefinedVarError(f"Variable {op} is not defined")
        return current_env[op]
        
    for instr in instrs:
        if instr.kind == 'copy':
            current_env[instr.dest] = get_val(instr.a)
        elif instr.kind == 'unary':
            val = get_val(instr.a)
            if instr.op == 'neg':
                current_env[instr.dest] = -val
            else:
                raise ValueError(f"Unknown unary op {instr.op}")
        elif instr.kind == 'binary':
            v1 = get_val(instr.a)
            v2 = get_val(instr.b)
            if instr.op == '+':
                res = v1 + v2
            elif instr.op == '-':
                res = v1 - v2
            elif instr.op == '*':
                res = v1 * v2
            elif instr.op == '/':
                res = safe_div(v1, v2)
            elif instr.op == '%':
                res = safe_mod(v1, v2)
            else:
                raise ValueError(f"Unknown binary op {instr.op}")
            current_env[instr.dest] = res
            
    return current_env
