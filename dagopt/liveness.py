"""
Liveness Analysis.
"""
from typing import Set, Optional
from dagopt.tac import is_temp
from dagopt.blocks import BasicBlock
from dagopt.verify import get_terminator_operands

def compute_live_out(block: BasicBlock, temp_regex: str, override: Optional[Set[str]] = None) -> Set[str]:
    live_out = set()
    
    if override is not None:
        live_out.update(override)
    else:
        # Default: all program variables (non-temporaries) that appear in the block
        for instr in block.instrs:
            if isinstance(instr.a, str) and not is_temp(instr.a, temp_regex):
                live_out.add(instr.a)
            if isinstance(instr.b, str) and not is_temp(instr.b, temp_regex):
                live_out.add(instr.b)
            if instr.dest and not is_temp(instr.dest, temp_regex):
                live_out.add(instr.dest)
                
    # Plus any variable read by the terminator (even if it's a temporary)
    if block.terminator:
        for op in get_terminator_operands(block.terminator):
            if isinstance(op, str):
                live_out.add(op)
                
    return live_out

