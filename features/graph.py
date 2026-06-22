import networkx as nx
import matplotlib.pyplot as plt
import random
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D

from db import session, Memory, CHO
from services.metadata import extract_metadata, get_memory_title
from features.tree_views import show_cho_tree


# =========================
# COLOR MAP PER CHO
# =========================
def get_cho_color_map(cho_ids):
    random.seed(42)

    palette = [
        "#66c2a5", "#fc8d62", "#8da0cb",
        "#e78ac3", "#a6d854", "#ffd92f",
        "#e5c494", "#b3b3b3"
    ]

    return {cid: palette[i % len(palette)] for i, cid in enumerate(cho_ids)}


# =========================
# CATEGORY COLOR
# =========================
def get_category_color(field):
    if field.startswith("dc:") or field.startswith("dcterms:"):
        return "#ffcc66"  # CHO metadata
    elif field.startswith("oaf:") or field.startswith("rdaGr2:"):
        return "#66b3ff"  # Agent metadata
    else:
        return "#cccccc"


# =========================
# MAIN GRAPH FUNCTION
# =========================
def generate_graph(frame, state):
    from tkinter import messagebox

    if not state.current_cho and not state.current_memory:
        messagebox.showinfo("Info", "Select CHO or Memory first")
        return

    if state.canvas:
        state.canvas.get_tk_widget().destroy()
        state.canvas = None

    G = nx.Graph()
    node_types = {}
    node_data = {}

    # =========================
    # BUILD GRAPH
    # =========================
    if state.current_memory:
        m = state.current_memory

        for md in extract_metadata(m.text):
            mn = f"memory:{m.custom_id}"
            cn = f"CHO:{md['cho']}"
            tn = f"tag:{md['value']}"

            G.add_edges_from([(mn, cn), (cn, tn)])

            node_types[mn] = "memory"
            node_types[cn] = "cho"
            node_types[tn] = "tag"

            node_data[mn] = m
            node_data[cn] = md["cho"]
            node_data[tn] = md

    else:
        cid = state.current_cho

        for m in session.query(Memory):
            for md in extract_metadata(m.text):
                if md["cho"] != cid:
                    continue

                mn = f"memory:{m.custom_id}"
                tn = f"tag:{md['value']}"
                cn = f"CHO:{cid}"

                G.add_edges_from([(mn, tn), (tn, cn)])

                node_types[mn] = "memory"
                node_types[tn] = "tag"
                node_types[cn] = "cho"

                node_data[mn] = m
                node_data[tn] = md
                node_data[cn] = cid

    if not G.nodes:
        messagebox.showinfo("Info", "No data to display")
        return

    # =========================
    # CLUSTER LAYOUT
    # =========================
    pos = {}
    offset = 0
    cho_groups = {}

    for n in G.nodes:
        if node_types[n] == "cho":
            cho_groups.setdefault(node_data[n], []).append(n)

    for node in G.nodes:
        if node_types[node] == "tag":
            md = node_data[node]
            cho_groups.setdefault(md["cho"], []).append(node)
    
        elif node_types[node] == "memory":
            if state.current_memory:
                # ✅ keep memory grouped with its CHO
                cho_groups.setdefault(
                    state.current_memory.custom_id,
                    []
                ).append(node)
    for node in G.nodes:
        if node_types[node] == "cho":
            cho_groups.setdefault(node_data[node], []).append(node)

    for _, nodes in cho_groups.items():
        sub = G.subgraph(nodes)
        sub_pos = nx.kamada_kawai_layout(sub, center=(offset, 0))
        pos.update(sub_pos)
        offset += 3

    if len(pos) != len(G.nodes):
        pos = nx.kamada_kawai_layout(G)

    # =========================
    # DRAW GRAPH
    # =========================
    fig = plt.Figure()
    ax = fig.add_subplot(111)

    for node in G.nodes:
        ntype = node_types[node]

        # COLOR
        if ntype == "memory":
            color = "#9ecae1"
        elif ntype == "tag":
            color = get_category_color(node_data[node]["field"])
        elif ntype == "cho":
            color = "#66c2a5"
        else:
            color = "grey"

        # Highlight selected memory
        if ntype == "memory" and state.current_memory == node_data[node]:
            color = "red"

        # SIZE
        if ntype == "cho":
            size = 1400
        elif ntype == "memory":
            size = 1000
        else:
            size = 700

        # SHAPE
        shape = "o"
        if ntype == "memory":
            shape = "s"
        elif ntype == "tag":
            shape = "h"

        nx.draw_networkx_nodes(
            G, pos,
            nodelist=[node],
            node_color=color,
            node_shape=shape,
            node_size=size,
            ax=ax
        )
    # =========================
    # EDGES (color-based)
    # =========================
    edge_colors = []
    
    for u, v in G.edges:
        # Normalize direction (edges are undirected)
        nodes = (u, v)
    
        # ✅ Memory → Tag (annotation)
        if "memory:" in u or "memory:" in v:
            edge_colors.append("#444444")   # dark grey
    
        # ✅ Tag → CHO (classification)
        else:
            edge_colors.append("#bbbbbb")   # light grey
    
    nx.draw_networkx_edges(
        G,
        pos,
        width=2,                 # ✅ uniform thickness
        edge_color=edge_colors,
        ax=ax
    )

    # =========================
    # LABELS
    # =========================
    labels = {}
    for node in G.nodes:
        ntype = node_types[node]
        data = node_data[node]

        if ntype == "memory":
            labels[node] = get_memory_title(data.text, data.custom_id)

        elif ntype == "tag":
            labels[node] = data["field"].split(":")[-1]

        elif ntype == "cho":
            cho_obj = session.query(CHO).filter_by(custom_id=data).first()
            labels[node] = cho_obj.title if cho_obj else data

    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, ax=ax)

    # =========================
    # LEGEND
    # =========================
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='CHO',
               markerfacecolor='#66c2a5', markersize=10),

        Line2D([0], [0], marker='s', color='w', label='Memory',
               markerfacecolor='#9ecae1', markersize=10),

        Line2D([0], [0], marker='h', color='w', label='CHO Metadata',
               markerfacecolor='#ffcc66', markersize=10),

        Line2D([0], [0], marker='h', color='w', label='Agent Metadata',
               markerfacecolor='#66b3ff', markersize=10),
    ]

    ax.legend(handles=legend_elements)

    # =========================
    # CONTEXT TITLE (NEW)
    # =========================
    if state.current_memory:
        title = f"Memory View: {state.current_memory.custom_id}"
    else:
        title = f"CHO View: {state.current_cho}"

    ax.set_title(title)

    ax.margins(0.2)

    # =========================
    # CLICK INTERACTION
    # =========================
    def on_click(event):
        if event.xdata is None or event.ydata is None:
            return
    
        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:
    
                # =========================
                # CHO CLICK
                # =========================
                if node.startswith("CHO:"):
                    cho_id = node_data[node]
    
                    state.current_cho = cho_id
                    state.current_memory = None
    
                    if hasattr(state, "metadata_panel"):
                        state.metadata_panel.show_cho_metadata(cho_id)
    
                    generate_graph(state.graph_frame, state)
    
                # =========================
                # MEMORY CLICK
                # =========================
                elif node.startswith("memory:"):
                    state.current_memory = node_data[node]
    
                    if hasattr(state, "metadata_panel"):
                        state.metadata_panel.refresh()
    
                    generate_graph(state.graph_frame, state)
    
                # =========================
                # TAG CLICK
                # =========================
                else:
                    from tkinter import messagebox
    
                    md = node_data[node]
                    messagebox.showinfo(
                        "Tag",
                        f"{md['field']} → {md['value']}"
                    )
    
                break

    fig.canvas.mpl_connect("button_press_event", on_click)

    # =========================
    # EMBED IN TK
    # =========================
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    state.canvas = canvas