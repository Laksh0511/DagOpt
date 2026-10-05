"""
Graphviz DOT Export.
"""
from typing import Set
from dagopt.dag import DAG

def export_dot(dag: DAG, live_nodes: Set[int]) -> str:
    lines = [
        "digraph DAG {",
        "  rankdir=BT;",
        "  ordering=out;",
    ]
    
    # Calculate parents to find shared nodes
    parents = {n.id: 0 for n in dag.nodes}
    for n in dag.nodes:
        for c in n.children:
            parents[c] += 1
            
    for n in dag.nodes:
        is_live = n.id in live_nodes
        is_shared = parents[n.id] > 1
        
        # Style
        style_parts = []
        if not is_live:
            style_parts.append("style=dashed")
            style_parts.append("color=grey")
            style_parts.append("fontcolor=grey")
        else:
            if is_shared:
                style_parts.append("style=filled")
                style_parts.append("fillcolor=lightblue")
                
        if n.op in ('var', 'const'):
            style_parts.append("shape=box")
            
        style_str = f" [{', '.join(style_parts)}]" if style_parts else ""
        
        # Label
        label_text = f"{n.op} {n.value}" if n.op in ('var', 'const') else n.op
        if n.labels:
            label_text += f" \\n[{', '.join(n.labels)}]"
            
        lines.append(f'  n{n.id} [label="{label_text}"{style_str}];')
        
        for c in n.children:
            edge_style = ""
            if not is_live or c not in live_nodes:
                edge_style = " [style=dashed, color=grey]"
            lines.append(f"  n{n.id} -> n{c}{edge_style};")
            
    lines.append("}")
    return "\n".join(lines)

