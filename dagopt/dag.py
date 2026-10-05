"""
DAG Construction.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from dagopt.tac import Instr
from dagopt.simplify import try_simplify

@dataclass
class Node:
    id: int
    op: str
    value: str | int | None
    children: Tuple[int, ...]
    labels: List[str]

class DAG:
    def __init__(self):
        self.nodes: List[Node] = []
        self.table: Dict[Tuple, int] = {}
        self.cur: Dict[str, int] = {}
        self.leaf_var: Dict[str, int] = {}
        self.leaf_const: Dict[int, int] = {}
        self.cse_hits: int = 0
        self.constants_folded: int = 0
        self.algebraic_simplifications: int = 0

def build_dag(block_instrs: List[Instr], no_fold: bool = False, no_algebra: bool = False, no_commute: bool = False) -> DAG:
    dag = DAG()
    
    def add_node(op: str, value: str | int | None, children: Tuple[int, ...]) -> int:
        n_id = len(dag.nodes)
        node = Node(id=n_id, op=op, value=value, children=children, labels=[])
        dag.nodes.append(node)
        return n_id

    def node_for(operand: str | int) -> int:
        if isinstance(operand, int):
            if operand in dag.leaf_const:
                return dag.leaf_const[operand]
            n_id = add_node('const', operand, ())
            dag.leaf_const[operand] = n_id
            return n_id
        else:
            if operand in dag.cur:
                return dag.cur[operand]
            n_id = add_node('var', operand, ())
            dag.nodes[n_id].labels.append(operand)
            dag.leaf_var[operand] = n_id
            dag.cur[operand] = n_id
            return n_id

    def bind(x: str, n: int):
        if x in dag.cur:
            old_n = dag.cur[x]
            if x in dag.nodes[old_n].labels:
                dag.nodes[old_n].labels.remove(x)
        dag.nodes[n].labels.append(x)
        dag.cur[x] = n

    for instr in block_instrs:
        if instr.kind == 'copy':
            c = node_for(instr.a)
            bind(instr.dest, c)
            
        elif instr.kind == 'unary':
            c = node_for(instr.a)
            
            if not no_fold or not no_algebra:
                simplified = try_simplify(dag, 'neg', (c,))
                if simplified[0]:
                    kind, val = simplified[1]
                    if kind == 'const' and not no_fold:
                        dag.constants_folded += 1
                        n = node_for(val)
                        bind(instr.dest, n)
                        continue
                    elif kind != 'const' and not no_algebra:
                        dag.algebraic_simplifications += 1
                        n = val
                        bind(instr.dest, n)
                        continue
                
            key = ('neg', c)
            if key in dag.table:
                dag.cse_hits += 1
                n = dag.table[key]
            else:
                n = add_node('neg', None, (c,))
                dag.table[key] = n
            bind(instr.dest, n)
            
        elif instr.kind == 'binary':
            l = node_for(instr.a)
            r = node_for(instr.b)
            
            if not no_fold or not no_algebra:
                simplified = try_simplify(dag, instr.op, (l, r))
                if simplified[0]:
                    kind, val = simplified[1]
                    if kind == 'const' and not no_fold:
                        dag.constants_folded += 1
                        n = node_for(val)
                        bind(instr.dest, n)
                        continue
                    elif kind != 'const' and not no_algebra:
                        dag.algebraic_simplifications += 1
                        n = val
                        bind(instr.dest, n)
                        continue
                
            if not no_commute and instr.op in ('+', '*'):
                key = (instr.op, min(l, r), max(l, r))
            else:
                key = (instr.op, l, r)
                
            if key in dag.table:
                dag.cse_hits += 1
                n = dag.table[key]
            else:
                n = add_node(instr.op, None, (l, r))
                dag.table[key] = n
            bind(instr.dest, n)
            
    return dag

def dag_summary(dag: DAG) -> str:
    lines = []
    for n in dag.nodes:
        labels_str = f" [{', '.join(n.labels)}]" if n.labels else ""
        if n.op in ('var', 'const'):
            lines.append(f"n{n.id}: {n.op} {n.value}{labels_str}")
        elif n.op == 'neg':
            lines.append(f"n{n.id}: {n.op} (n{n.children[0]}){labels_str}")
        else:
            lines.append(f"n{n.id}: {n.op} (n{n.children[0]}, n{n.children[1]}){labels_str}")
    return "\n".join(lines)

def get_live_nodes(dag: DAG, live_out: Set[str], terminator_reads: Set[str]) -> Set[int]:
    live_nodes = set()
    
    # 1. Roots from live-out variables
    for var in live_out:
        if var in dag.cur:
            live_nodes.add(dag.cur[var])
            
    # 2. Roots from terminator reads
    for var in terminator_reads:
        if var in dag.cur:
            live_nodes.add(dag.cur[var])
            
    # Also we should keep leaves that are read?
    # Mark reachable
    worklist = list(live_nodes)
    while worklist:
        n_id = worklist.pop()
        for child_id in dag.nodes[n_id].children:
            if child_id not in live_nodes:
                live_nodes.add(child_id)
                worklist.append(child_id)
                
    return live_nodes
