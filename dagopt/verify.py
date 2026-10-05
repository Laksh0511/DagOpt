"""
Equivalence Checker and Fuzzer.
"""
import random
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Any
from dagopt.tac import Instr
from dagopt.interp import interpret_block, collect_reads_before_writes

@dataclass
class VerifyResult:
    passed: bool
    trials_run: int
    trials_skipped: int
    failure_info: Optional[Dict[str, Any]] = None

def get_terminator_operands(instr: Instr) -> List[str]:
    ops = []
    if instr.kind == 'goto':
        pass
    elif instr.kind == 'cond':
        if isinstance(instr.a, str): ops.append(instr.a)
        if isinstance(instr.b, str): ops.append(instr.b)
    return ops

def verify_block(original: List[Instr], optimized: List[Instr], live_out: Set[str], trials: int = 200, seed: int = 0) -> VerifyResult:
    if trials == 0:
        return VerifyResult(True, 0, 0)
        
    rng = random.Random(seed)
    
    # Extract interior instructions
    orig_interior = [i for i in original if i.kind not in ('goto', 'cond')]
    opt_interior = [i for i in optimized if i.kind not in ('goto', 'cond')]
    
    orig_terminator = original[-1] if original and original[-1].kind in ('goto', 'cond') else None
    opt_terminator = optimized[-1] if optimized and optimized[-1].kind in ('goto', 'cond') else None

    # Collect reads
    reads = collect_reads_before_writes(orig_interior)
    if orig_terminator:
        for op in get_terminator_operands(orig_terminator):
            # If a terminator operand is read before being written, it must be provided
            if op not in collect_reads_before_writes(orig_interior) and op not in [i.dest for i in orig_interior if i.dest]:
                reads.add(op)
    
    trials_run = 0
    trials_skipped = 0
    
    for _ in range(trials):
        env = {}
        for r in reads:
            # Biased towards 0, 1, -1
            r_val = rng.random()
            if r_val < 0.1:
                env[r] = 0
            elif r_val < 0.2:
                env[r] = 1
            elif r_val < 0.3:
                env[r] = -1
            else:
                env[r] = rng.randint(-20, 20)
                
        try:
            orig_env = interpret_block(orig_interior, env)
        except ZeroDivisionError:
            trials_skipped += 1
            continue
            
        try:
            opt_env = interpret_block(opt_interior, env)
        except ZeroDivisionError:
            return VerifyResult(False, trials_run, trials_skipped, {
                'reason': 'Optimized code faulted while original did not',
                'inputs': env
            })
            
        # Check live-out variables
        for var in live_out:
            if var in orig_env and orig_env[var] != opt_env.get(var):
                return VerifyResult(False, trials_run, trials_skipped, {
                    'reason': f"Mismatch on live-out variable '{var}'",
                    'inputs': env,
                    'orig_env': orig_env,
                    'opt_env': opt_env
                })
                
        # Check terminator operands
        if orig_terminator and opt_terminator:
            for orig_op, opt_op in zip(get_terminator_operands(orig_terminator), get_terminator_operands(opt_terminator)):
                v_orig = orig_env.get(orig_op, env.get(orig_op))
                v_opt = opt_env.get(opt_op, env.get(opt_op))
                if v_orig != v_opt:
                    return VerifyResult(False, trials_run, trials_skipped, {
                        'reason': f"Mismatch on terminator operand: {orig_op}({v_orig}) vs {opt_op}({v_opt})",
                        'inputs': env,
                        'orig_env': orig_env,
                        'opt_env': opt_env
                    })
                    
        trials_run += 1
        
    return VerifyResult(True, trials_run, trials_skipped)

def generate_random_block(seed: int, n_vars: int = 4, n_temps: int = 3, length: Tuple[int, int] = (3, 15)) -> List[Instr]:
    rng = random.Random(seed)
    
    program_vars = [chr(ord('a') + i) for i in range(n_vars)]
    temps = [f"t{i}" for i in range(1, n_temps + 1)]
    
    all_vars = program_vars + temps
    
    instrs = []
    num_instrs = rng.randint(*length)
    
    ops_bin = ['+', '-', '*', '/', '%']
    
    # Keep track of expressions we've generated to bias towards CSE
    exprs = []
    
    for _ in range(num_instrs):
        dest = rng.choice(all_vars)
        if exprs and rng.random() < 0.3:
            # Re-use an existing expression (CSE opportunity)
            op, a, b = rng.choice(exprs)
            instrs.append(Instr('binary', dest, op, a, b, None))
        else:
            op = rng.choice(ops_bin)
            a = rng.choice(program_vars + [rng.randint(-5, 5)])
            b = rng.choice(program_vars + [rng.randint(-5, 5)])
            instrs.append(Instr('binary', dest, op, a, b, None))
            exprs.append((op, a, b))
            
    return instrs
