"""
Code Generation from DAG.
"""
from typing import List, Set, Dict, Tuple
from dagopt.tac import Instr, is_temp
from dagopt.dag import DAG, Node
from dagopt.blocks import BasicBlock
from dagopt.liveness import compute_live_out
from dagopt.verify import get_terminator_operands

class Item:
    def __init__(self, kind: str, dest: str, op: str | None, a: str | int | None, b: str | int | None, node_id: int):
        self.kind = kind
        self.dest = dest
        self.op = op
        self.a = a
        self.b = b
        self.node_id = node_id
        self.reads_initial: Set[str] = set()
        self.reads_computed: Set[str] = set()
        
    def __repr__(self):
        return f"{self.dest} = {self.a} {self.op or ''} {self.b or ''}"

class CodeGenerator:
    def __init__(self, dag: DAG, live_nodes: Set[int], live_out: Set[str], temp_regex: str, terminator: Instr | None):
        self.dag = dag
        self.live_nodes = live_nodes
        self.live_out = live_out
        self.temp_regex = temp_regex
        self.terminator = terminator
        self.temp_counter = 1
        
    def _new_temp(self) -> str:
        t = f"_n{self.temp_counter}"
        self.temp_counter += 1
        return t
        
    def choose_name(self, n: Node) -> str:
        if n.op == 'const':
            return str(n.value)
        if n.op == 'var':
            return str(n.value)
            
        live_labels = [lbl for lbl in n.labels if lbl in self.live_out]
        prog_vars = [lbl for lbl in live_labels if not is_temp(lbl, self.temp_regex)]
        
        if prog_vars:
            return prog_vars[0]
        if live_labels:
            return live_labels[0]
        if n.labels:
            return n.labels[0]
        return self._new_temp()

    def generate(self) -> List[Instr]:
        names = {}
        for n_id in self.live_nodes:
            names[n_id] = self.choose_name(self.dag.nodes[n_id])
            
        emit_items: List[Item] = []
        
        for n_id in self.live_nodes:
            n = self.dag.nodes[n_id]
            target_name = names[n_id]
            
            if n.op not in ('var', 'const'):
                c1 = self.dag.nodes[n.children[0]]
                c1_name = names[n.children[0]]
                
                if len(n.children) == 1:
                    item = Item('unary', target_name, n.op, c1_name, None, n_id)
                    if c1.op == 'var':
                        item.reads_initial.add(str(c1.value))
                    elif isinstance(c1_name, str):
                        item.reads_computed.add(c1_name)
                    emit_items.append(item)
                else:
                    c2 = self.dag.nodes[n.children[1]]
                    c2_name = names[n.children[1]]
                    item = Item('binary', target_name, n.op, c1_name, c2_name, n_id)
                    
                    if c1.op == 'var':
                        item.reads_initial.add(str(c1.value))
                    elif isinstance(c1_name, str):
                        item.reads_computed.add(c1_name)
                        
                    if c2.op == 'var':
                        item.reads_initial.add(str(c2.value))
                    elif isinstance(c2_name, str):
                        item.reads_computed.add(c2_name)
                        
                    emit_items.append(item)
                    
            for lbl in n.labels:
                if lbl in self.live_out and lbl != target_name:
                    item = Item('copy', lbl, None, target_name, None, n_id)
                    if n.op == 'var':
                        item.reads_initial.add(str(n.value))
                    elif isinstance(target_name, str):
                        item.reads_computed.add(target_name)
                    emit_items.append(item)
                    
        return self._schedule(emit_items, names)

    def _schedule(self, items: List[Item], names: Dict[int, str]) -> List[Instr]:
        adj: Dict[Item, Set[Item]] = {i: set() for i in items}
        
        def build_edges():
            for i in items:
                if i not in adj:
                    adj[i] = set()
                else:
                    adj[i].clear()
                
            def_map = {i.dest: i for i in items if i.dest}
            for j in items:
                for v in j.reads_computed:
                    if v in def_map:
                        i = def_map[v]
                        adj[i].add(j)
                for v in j.reads_initial:
                    if v in def_map:
                        i = def_map[v]
                        adj[j].add(i)

        build_edges()
        
        scheduled = []
        
        while items:
            in_degree = {i: 0 for i in items}
            for u in items:
                for v in adj[u]:
                    if v in in_degree:
                        in_degree[v] += 1
                        
            ready = [i for i in items if in_degree[i] == 0]
            
            if ready:
                # Tie-breaker: node creation order (node_id)
                ready.sort(key=lambda x: x.node_id)
                u = ready[0]
                scheduled.append(u)
                items.remove(u)
            else:
                # Cycle detected! Find a WAR edge to break
                def_map = {i.dest: i for i in items if i.dest}
                broken = False
                for j in items:
                    for v in list(j.reads_initial):
                        if v in def_map:
                            i = def_map[v]
                            # Break WAR edge j -> i on variable v
                            fresh = self._new_temp()
                            copy_item = Item('copy', fresh, None, v, None, -1)
                            copy_item.reads_initial.add(v)
                            
                            # j now reads computed fresh instead of initial v
                            j.reads_initial.remove(v)
                            j.reads_computed.add(fresh)
                            if j.a == v: j.a = fresh
                            if j.b == v: j.b = fresh
                            
                            items.append(copy_item)
                            build_edges()
                            broken = True
                            break
                    if broken:
                        break
                
                if not broken:
                    raise RuntimeError("Cycle without WAR edges found! This should be impossible.")
                    
        # Convert Items to Instrs
        final_instrs = []
        for it in scheduled:
            a_val = int(it.a) if isinstance(it.a, str) and (it.a.isdigit() or (it.a.startswith('-') and it.a[1:].isdigit())) else it.a
            b_val = int(it.b) if isinstance(it.b, str) and (it.b.isdigit() or (it.b.startswith('-') and it.b[1:].isdigit())) else it.b
            final_instrs.append(Instr(it.kind, it.dest, it.op, a_val, b_val, None))
            
        # Rewrite terminator
        if self.terminator:
            def rewrite_op(op):
                if isinstance(op, str) and op in self.dag.cur:
                    n_id = self.dag.cur[op]
                    if n_id in names:
                        return names[n_id]
                return op
                
            if self.terminator.kind == 'goto':
                final_instrs.append(self.terminator)
            elif self.terminator.kind == 'cond':
                new_a = rewrite_op(self.terminator.a)
                new_b = rewrite_op(self.terminator.b)
                final_instrs.append(Instr('cond', None, self.terminator.op, new_a, new_b, self.terminator.target))
                
        return final_instrs

def optimize_block(block: BasicBlock, temp_regex: str, override_live: Set[str] = None, no_fold: bool = False, no_algebra: bool = False, no_commute: bool = False) -> List[Instr]:
    from dagopt.dag import build_dag, get_live_nodes
    
    live_out = compute_live_out(block, temp_regex, override_live)
    dag = build_dag(block.instrs, no_fold, no_algebra, no_commute)
    
    terminator_reads = set()
    if block.terminator:
        for op in get_terminator_operands(block.terminator):
            if isinstance(op, str):
                terminator_reads.add(op)
                
    live_nodes = get_live_nodes(dag, live_out, terminator_reads)
    
    cg = CodeGenerator(dag, live_nodes, live_out, temp_regex, block.terminator)
    return cg.generate()
