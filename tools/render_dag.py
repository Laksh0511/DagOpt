"""
Render a DAG from a .tac file and save the visualization as a PNG.
Uses matplotlib + networkx — no external Graphviz binary required.
"""
import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tac_file")
    parser.add_argument("-o", default=None, help="Output PNG path")
    parser.add_argument("--live-out", default="", help="Comma-separated live-out vars")
    parser.add_argument("--block", type=int, default=0, help="Which block to visualize")
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

    dag = build_dag(block.instrs)

    terminator_reads = set()
    if block.terminator:
        for op in get_terminator_operands(block.terminator):
            if isinstance(op, str):
                terminator_reads.add(op)

    live_nodes = get_live_nodes(dag, live_out, terminator_reads)

    # --- build networkx graph ---
    try:
        import networkx as nx
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError as e:
        print(f"Missing dependency: {e}. Run: pip install networkx matplotlib")
        sys.exit(1)

    G = nx.DiGraph()
    node_labels = {}
    node_colors = []
    node_shapes_circle = []   # internal op nodes
    node_shapes_box = []      # leaf nodes (var/const)

    for n in dag.nodes:
        G.add_node(n.id)
        if n.op in ("var", "const"):
            label = f"{n.value}"
        else:
            label = n.op
        if n.labels:
            label += f"\n[{', '.join(n.labels)}]"
        node_labels[n.id] = label

        if n.id in live_nodes:
            # count how many parents point here
            in_deg = sum(1 for m in dag.nodes if n.id in m.children)
            node_colors.append("#4FC3F7" if in_deg > 1 else "#A5D6A7")
        else:
            node_colors.append("#B0BEC5")

        if n.op in ("var", "const"):
            node_shapes_box.append(n.id)
        else:
            node_shapes_circle.append(n.id)

        for c in n.children:
            G.add_edge(n.id, c)

    # layout: reverse topological so leaves are at the bottom
    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except Exception:
        pos = nx.spring_layout(G, seed=42, k=2.5)

    fig, ax = plt.subplots(figsize=(max(8, len(dag.nodes) * 1.4), 6))
    ax.set_title(
        f"DAG — Block {args.block}  |  "
        f"Nodes: {len(dag.nodes)}  CSE hits: {dag.cse_hits}  "
        f"Folded: {dag.constants_folded}",
        fontsize=12, fontweight="bold"
    )
    ax.axis("off")

    # Draw box-shaped leaves separately as rectangles via FancyBboxPatch
    box_nodes = [n for n in dag.nodes if n.id in node_shapes_box]
    circle_nodes = [n for n in dag.nodes if n.id in node_shapes_circle]

    nx.draw_networkx_nodes(
        G, pos,
        nodelist=[n.id for n in circle_nodes],
        node_color=[node_colors[n.id] for n in circle_nodes],
        node_size=1800, ax=ax
    )
    nx.draw_networkx_nodes(
        G, pos,
        nodelist=[n.id for n in box_nodes],
        node_color=[node_colors[n.id] for n in box_nodes],
        node_size=1800, ax=ax,
        node_shape="s"
    )
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8, ax=ax)
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        arrows=True, arrowsize=18,
        edge_color="#546E7A",
        connectionstyle="arc3,rad=0.05"
    )

    # Legend
    patches = [
        mpatches.Patch(color="#A5D6A7", label="Live node"),
        mpatches.Patch(color="#4FC3F7", label="Shared (CSE)"),
        mpatches.Patch(color="#B0BEC5", label="Dead node"),
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=9)

    out_path = args.o or os.path.join(os.path.expanduser("~"), "Desktop", "dag_block0.png")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    main()
