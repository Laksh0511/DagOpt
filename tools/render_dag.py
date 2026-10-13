"""
Render a DAG from a .tac file and save the visualization as a PNG.
Uses matplotlib + networkx — no external Graphviz binary required.
"""
import sys
import os
import argparse
import math


def hierarchical_layout(G, dag_nodes):
    """
    Custom top-down BFS layout.
    Root nodes (no incoming edges in G) sit at the top (y=1.0),
    leaves (no outgoing edges) at the bottom (y=0.0).
    """
    import collections

    # Build adjacency from node id
    children_map = {n.id: list(n.children) for n in dag_nodes}
    parent_map = {n.id: [] for n in dag_nodes}
    for n in dag_nodes:
        for c in n.children:
            parent_map[c].append(n.id)

    # BFS levels from roots (nodes with no parents)
    roots = [n.id for n in dag_nodes if not parent_map[n.id]]
    if not roots:
        roots = [dag_nodes[0].id]

    levels = {}
    queue = collections.deque(roots)
    for r in roots:
        levels[r] = 0

    while queue:
        nid = queue.popleft()
        for child in children_map.get(nid, []):
            new_level = levels[nid] + 1
            if child not in levels or levels[child] < new_level:
                levels[child] = new_level
                queue.append(child)

    # Group nodes by level
    max_level = max(levels.values()) if levels else 0
    by_level = collections.defaultdict(list)
    for nid, lv in levels.items():
        by_level[lv].append(nid)

    pos = {}
    for lv, nodes_at_level in by_level.items():
        n_nodes = len(nodes_at_level)
        for i, nid in enumerate(sorted(nodes_at_level)):
            x = (i + 1) / (n_nodes + 1)
            y = 1.0 - lv / (max_level + 1) if max_level > 0 else 0.5
            pos[nid] = (x, y)

    return pos


def main():
    parser = argparse.ArgumentParser(description="Render DAG from a TAC file to PNG")
    parser.add_argument("tac_file", help="Path to .tac input file")
    parser.add_argument("-o", default=None, help="Output PNG path (default: dag_block0.png)")
    parser.add_argument("--live-out", default="", help="Comma-separated live-out variables")
    parser.add_argument("--block", type=int, default=0, help="Which basic block to visualize (default: 0)")
    parser.add_argument("--no-fold", action="store_true", help="Disable constant folding")
    parser.add_argument("--no-algebra", action="store_true", help="Disable algebraic identities")
    parser.add_argument("--no-commute", action="store_true", help="Disable commutativity canonicalization")
    args = parser.parse_args()

    # --- core dagopt imports ---
    from dagopt.tac import parse_tac
    from dagopt.blocks import build_blocks
    from dagopt.dag import build_dag, get_live_nodes
    from dagopt.liveness import compute_live_out
    from dagopt.codegen import get_terminator_operands

    with open(args.tac_file) as f:
        text = f.read()

    instrs = parse_tac(text)
    blocks = build_blocks(instrs)

    if args.block >= len(blocks):
        print(f"Block {args.block} not found (only {len(blocks)} blocks).")
        sys.exit(1)

    block = blocks[args.block]
    override = set(args.live_out.split(",")) if args.live_out else None
    live_out = compute_live_out(block, r"^_(t|n)\d+$", override)

    dag = build_dag(block.instrs, args.no_fold, args.no_algebra, args.no_commute)

    terminator_reads = set()
    if block.terminator:
        for op in get_terminator_operands(block.terminator):
            if isinstance(op, str):
                terminator_reads.add(op)

    live_nodes = get_live_nodes(dag, live_out, terminator_reads)

    # Count parents for each node (to detect CSE / shared nodes)
    parent_count = {n.id: 0 for n in dag.nodes}
    for n in dag.nodes:
        for c in n.children:
            parent_count[c] += 1

    # --- build networkx graph ---
    try:
        import networkx as nx
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch
    except ImportError as e:
        print(f"Missing dependency: {e}\nRun: pip install networkx matplotlib")
        sys.exit(1)

    G = nx.DiGraph()
    node_labels = {}
    node_color_map = {}

    for n in dag.nodes:
        G.add_node(n.id)

        # Build label
        if n.op == "var":
            lbl = str(n.value)
        elif n.op == "const":
            lbl = str(n.value)
        else:
            lbl = n.op

        # Attach variable labels (aliases)
        if n.labels:
            lbl += "\n[" + ", ".join(n.labels) + "]"
        node_labels[n.id] = lbl

        # Colour logic
        is_live = n.id in live_nodes
        is_shared = parent_count[n.id] > 1
        if not is_live:
            node_color_map[n.id] = "#B0BEC5"   # grey — dead
        elif is_shared:
            node_color_map[n.id] = "#4FC3F7"   # blue — CSE shared
        else:
            node_color_map[n.id] = "#A5D6A7"   # green — live

        for c in n.children:
            G.add_edge(n.id, c)

    # Compute layout
    pos = hierarchical_layout(G, dag.nodes)

    # Separate leaf vs op nodes for different shapes
    leaf_ids = [n.id for n in dag.nodes if n.op in ("var", "const")]
    op_ids   = [n.id for n in dag.nodes if n.op not in ("var", "const")]

    fig_w = max(10, len(dag.nodes) * 1.8)
    fig_h = max(6,  (max(pos[n][1] for n in pos) + 1) * 3 if pos else 6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    title = (
        f"DAG — Block {args.block}   |   "
        f"Nodes: {len(dag.nodes)}   "
        f"CSE hits: {dag.cse_hits}   "
        f"Const-folded: {dag.constants_folded}   "
        f"Algebraic: {dag.algebraic_simplifications}"
    )
    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.15, 1.15)
    ax.axis("off")

    # Draw op nodes (circles)
    if op_ids:
        nx.draw_networkx_nodes(
            G, pos, nodelist=op_ids,
            node_color=[node_color_map[n] for n in op_ids],
            node_size=2200, node_shape="o", ax=ax,
            linewidths=1.5, edgecolors="#37474F"
        )

    # Draw leaf nodes (squares)
    if leaf_ids:
        nx.draw_networkx_nodes(
            G, pos, nodelist=leaf_ids,
            node_color=[node_color_map[n] for n in leaf_ids],
            node_size=2200, node_shape="s", ax=ax,
            linewidths=1.5, edgecolors="#37474F"
        )

    # Labels
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=9, font_weight="bold", ax=ax)

    # Edges — colour dead edges grey
    live_edges  = [(u, v) for u, v in G.edges() if u in live_nodes and v in live_nodes]
    dead_edges  = [(u, v) for u, v in G.edges() if (u, v) not in live_edges]

    nx.draw_networkx_edges(
        G, pos, edgelist=live_edges, ax=ax,
        arrows=True, arrowsize=22, arrowstyle="-|>",
        edge_color="#37474F", width=2.0,
        connectionstyle="arc3,rad=0.08",
        min_source_margin=28, min_target_margin=28,
    )
    nx.draw_networkx_edges(
        G, pos, edgelist=dead_edges, ax=ax,
        arrows=True, arrowsize=16, arrowstyle="-|>",
        edge_color="#90A4AE", width=1.0, style="dashed",
        connectionstyle="arc3,rad=0.08",
        min_source_margin=28, min_target_margin=28,
    )

    # Legend
    legend_patches = [
        mpatches.Patch(color="#A5D6A7", label="Live node"),
        mpatches.Patch(color="#4FC3F7", label="Shared / CSE node"),
        mpatches.Patch(color="#B0BEC5", label="Dead node (pruned)"),
        mpatches.Patch(color="white",   label="○ = operator   □ = var/const",
                       edgecolor="#37474F", linewidth=1),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9, framealpha=0.9)

    out_path = args.o or "dag_block0.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
