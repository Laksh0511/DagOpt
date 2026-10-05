import json
import csv
from dataclasses import dataclass, asdict
from typing import List
import sys

@dataclass
class BlockMetrics:
    block_id: int
    instrs_before: int
    instrs_after: int
    arith_before: int
    arith_after: int
    copy_before: int
    copy_after: int
    dag_nodes: int
    cse_hits: int
    constants_folded: int
    algebraic_simplifications: int
    dead_nodes_removed: int
    verification_passed: bool

@dataclass
class TotalMetrics:
    total_instrs_before: int = 0
    total_instrs_after: int = 0
    total_arith_before: int = 0
    total_arith_after: int = 0
    total_copy_before: int = 0
    total_copy_after: int = 0
    total_dag_nodes: int = 0
    total_cse_hits: int = 0
    total_constants_folded: int = 0
    total_algebraic_simplifications: int = 0
    total_dead_nodes_removed: int = 0
    total_verification_passed: bool = True
    
def print_metrics_table(blocks: List[BlockMetrics], total: TotalMetrics, out=sys.stdout):
    # Print as aligned table
    headers = [
        "Block", "InstrIn", "InstrOut", "ArithIn", "ArithOut", "CopyIn", "CopyOut", 
        "DAGNodes", "CSE", "ConstFold", "Algebraic", "DeadRm", "Verify"
    ]
    
    fmt = "{:<8} {:<9} {:<10} {:<9} {:<10} {:<8} {:<9} {:<10} {:<5} {:<11} {:<11} {:<8} {:<7}"
    out.write(fmt.format(*headers) + "\n")
    out.write("-" * 125 + "\n")
    
    for b in blocks:
        out.write(fmt.format(
            b.block_id, b.instrs_before, b.instrs_after, b.arith_before, b.arith_after,
            b.copy_before, b.copy_after, b.dag_nodes, b.cse_hits, b.constants_folded,
            b.algebraic_simplifications, b.dead_nodes_removed, str(b.verification_passed)
        ) + "\n")
        
    out.write("-" * 125 + "\n")
    out.write(fmt.format(
        "TOTAL", total.total_instrs_before, total.total_instrs_after, total.total_arith_before,
        total.total_arith_after, total.total_copy_before, total.total_copy_after,
        total.total_dag_nodes, total.total_cse_hits, total.total_constants_folded,
        total.total_algebraic_simplifications, total.total_dead_nodes_removed,
        str(total.total_verification_passed)
    ) + "\n")

def export_metrics_json(blocks: List[BlockMetrics], total: TotalMetrics, filename: str):
    data = {
        "blocks": [asdict(b) for b in blocks],
        "total": asdict(total)
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def export_metrics_csv(blocks: List[BlockMetrics], total: TotalMetrics, filename: str):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        headers = [
            "block_id", "instrs_before", "instrs_after", "arith_before", "arith_after",
            "copy_before", "copy_after", "dag_nodes", "cse_hits", "constants_folded",
            "algebraic_simplifications", "dead_nodes_removed", "verification_passed"
        ]
        writer.writerow(headers)
        for b in blocks:
            writer.writerow([getattr(b, h) for h in headers])
        
        # Add total row
        writer.writerow([
            "TOTAL", total.total_instrs_before, total.total_instrs_after,
            total.total_arith_before, total.total_arith_after,
            total.total_copy_before, total.total_copy_after,
            total.total_dag_nodes, total.total_cse_hits, total.total_constants_folded,
            total.total_algebraic_simplifications, total.total_dead_nodes_removed,
            total.total_verification_passed
        ])
