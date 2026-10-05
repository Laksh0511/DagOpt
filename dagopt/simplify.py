"""
Constant Folding and Algebraic Identities.
"""
from typing import Tuple, Any, Tuple as TupleType
from dagopt.tac import safe_div, safe_mod

def try_simplify(dag, op: str, children: TupleType[int, ...]) -> Tuple[bool, Any]:
    c1 = children[0]
    n1 = dag.nodes[c1]
    is_c1_const = n1.op == 'const'
    v1 = n1.value if is_c1_const else None
    
    if len(children) == 2:
        c2 = children[1]
        n2 = dag.nodes[c2]
        is_c2_const = n2.op == 'const'
        v2 = n2.value if is_c2_const else None
        
        # Constant folding
        if is_c1_const and is_c2_const:
            if op == '+': return True, ('const', v1 + v2)
            if op == '-': return True, ('const', v1 - v2)
            if op == '*': return True, ('const', v1 * v2)
            if op == '/':
                try: return True, ('const', safe_div(v1, v2))
                except ZeroDivisionError: pass
            if op == '%':
                try: return True, ('const', safe_mod(v1, v2))
                except ZeroDivisionError: pass
                
        # Algebraic identities
        if op == '+':
            if is_c1_const and v1 == 0: return True, ('node', c2)
            if is_c2_const and v2 == 0: return True, ('node', c1)
        elif op == '*':
            if is_c1_const and v1 == 1: return True, ('node', c2)
            if is_c2_const and v2 == 1: return True, ('node', c1)
            if is_c1_const and v1 == 0: return True, ('const', 0)
            if is_c2_const and v2 == 0: return True, ('const', 0)
        elif op == '-':
            if is_c2_const and v2 == 0: return True, ('node', c1)
            if c1 == c2: return True, ('const', 0)
        elif op == '/':
            if is_c2_const and v2 == 1: return True, ('node', c1)
            if c1 == c2: return True, ('const', 1)
            
    elif len(children) == 1:
        # Unary operations
        if op == 'neg':
            if is_c1_const:
                return True, ('const', -v1)
                
    return False, None
