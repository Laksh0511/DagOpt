"""
Basic Block Splitting.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from dagopt.tac import Instr

@dataclass
class BasicBlock:
    index: int
    instrs: List[Instr]
    terminator: Optional[Instr] = None
    successors: List[int] = field(default_factory=list)
    predecessors: List[int] = field(default_factory=list)

def build_blocks(instructions: List[Instr]) -> List[BasicBlock]:
    if not instructions:
        return []

    # Step 1: Identify leaders
    leaders = set()
    leaders.add(0)
    
    # Target of any jump
    jump_targets = set()
    for instr in instructions:
        if instr.kind in ('goto', 'cond') and instr.target:
            jump_targets.add(instr.target)
            
    for i, instr in enumerate(instructions):
        if instr.kind == 'label': # and instr.target in jump_targets:
            # We treat all labels as leaders for safety.
            leaders.add(i)
        elif instr.kind in ('goto', 'cond'):
            if i + 1 < len(instructions):
                leaders.add(i + 1)
                
    # Sort leaders
    leaders_list = sorted(list(leaders))
    
    # Step 2: Build blocks
    blocks: List[BasicBlock] = []
    for idx, start_idx in enumerate(leaders_list):
        end_idx = leaders_list[idx+1] if idx + 1 < len(leaders_list) else len(instructions)
        
        block_instrs = instructions[start_idx:end_idx]
        terminator = None
        if block_instrs and block_instrs[-1].kind in ('goto', 'cond'):
            terminator = block_instrs.pop()
            
        blocks.append(BasicBlock(index=idx, instrs=block_instrs, terminator=terminator))
        
    # Step 3: Compute CFG edges
    # Build label -> block_index mapping
    label_to_block = {}
    for block in blocks:
        # A block might have multiple labels at the start
        for instr in block.instrs:
            if instr.kind == 'label':
                label_to_block[instr.target] = block.index
            else:
                break # Labels are kept at the start
                
    for i, block in enumerate(blocks):
        # Default successor is the next block if it doesn't end with an unconditional goto
        if block.terminator:
            if block.terminator.kind == 'goto':
                if block.terminator.target in label_to_block:
                    target_idx = label_to_block[block.terminator.target]
                    block.successors.append(target_idx)
            elif block.terminator.kind == 'cond':
                # Conditional branches to target AND falls through to next block
                if block.terminator.target in label_to_block:
                    target_idx = label_to_block[block.terminator.target]
                    block.successors.append(target_idx)
                if i + 1 < len(blocks):
                    block.successors.append(i + 1)
        else:
            if i + 1 < len(blocks):
                block.successors.append(i + 1)
                
    # Fill predecessors
    for block in blocks:
        # deduplicate successors in case of strange goto next block
        block.successors = sorted(list(set(block.successors)))
        for succ_idx in block.successors:
            blocks[succ_idx].predecessors.append(block.index)
            
    # deduplicate predecessors
    for block in blocks:
        block.predecessors = sorted(list(set(block.predecessors)))
        
    return blocks
