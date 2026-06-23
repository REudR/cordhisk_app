import networkx as nx
import matplotlib.pyplot as plt
import random
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D

from db import session, Memory, CHO
from services.metadata import extract_metadata, get_memory_title
from utils import MetadataType
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
# METADATA TYPE COLORS
# =========================
def get_metadata_color(metadata_type, field):
    if metadata_type == MetadataType.MEMORY.value:
        return "#a1d99b"
    else:
        if field.startswith("dc:") or field.startswith("dcterms:"):
            return "#ffcc66"
        elif field.startswith("oaf:") or field.startswith("rdaGr2:"):
            return "#66b3ff"
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

            if md.get("type") == MetadataType.MEMORY.value:
                mmd_node = f"memory_metadata:{m.custom_id}:{md['field']}"
                
                G.add_edges_from([
                    (mn, cmd_node),   # Memory → metadata
                    (cmd_node, cn)    # metadata → CHO
                ])

                node_types[mn] = "memory"
                node_types[mmd_node] = "memory_metadata"

                node_data[mn] = m
                node_data[mmd_node] = md

            else:
                cn = f"CHO:{md['cho']}"
                cmd_node = f"cho_metadata:{md['cho']}:{md['field']}"

                G.add_edges_from([
                    (mn, cmd_node),   # Memory → metadata
                    (cmd_node, cn)    # metadata → CHO
                ])

                node_types[mn] = "memory"
                node_types[cn] = "cho"
                node_types[cmd_node] = "cho_metadata"

                node_data[mn] = m
                node_data[cn] = md["cho"]
                node_data[cmd_node] = md

    else:
        cid = state.current_cho
        
        for m in session.query(Memory):
        
            memory_connected = False
            memory_md = []
            cho_md = []
        
            # First pass: classify metadata
            for md in extract_metadata(m.text):
                if md.get("type") == MetadataType.MEMORY.value:
                    memory_md.append(md)
                else:
                    if md.get("cho") == cid:
                        memory_connected = True
                        cho_md.append(md)
        
            # ✅ Skip memories NOT linked to the CHO
            if not memory_connected:
                continue
        
            mn = f"memory:{m.custom_id}"
            node_types[mn] = "memory"
            node_data[mn] = m
        
            # ✅ Add CHO node once
            cn = f"CHO:{cid}"
            node_types[cn] = "cho"
            node_data[cn] = cid
        
            # =========================
            # ADD CHO METADATA (main connections)
            # =========================
            for md in cho_md:
                cmd_node = f"cho_metadata:{cid}:{md['field']}:{md['value']}"
        
                G.add_edges_from([
                    (mn, cmd_node),
                    (cmd_node, cn)
                ])
        
                node_types[cmd_node] = "cho_metadata"
                node_data[cmd_node] = md
        
            # =========================
            # OPTIONAL: include memory metadata
            # (only for connected memories)
            # =========================
            for md in memory_md:
                mmd_node = f"memory_metadata:{m.custom_id}:{md['field']}"
        
                G.add_edge(mn, mmd_node)
        
                node_types[mmd_node] = "memory_metadata"
                node_data[mmd_node] = md

    if not G.nodes:
        messagebox.showinfo("Info", "No data to display")
        return

    # =========================
    # LAYOUT (IMPROVED)
    # =========================
    pos = nx.kamada_kawai_layout(G, scale=3)

    # Small jitter to reduce overlap
    for k in pos:
        pos[k] = (
            pos[k][0] + random.uniform(-0.08, 0.08),
            pos[k][1] + random.uniform(-0.08, 0.08)
        )

    # =========================
    # DRAW GRAPH
    # =========================
    fig = plt.Figure()
    ax = fig.add_subplot(111)

    # DRAW NODES
    for node in G.nodes:
        ntype = node_types[node]

        if ntype == "memory":
            color = "#9ecae1"
        elif ntype == "memory_metadata":
            color = "#a1d99b"
        elif ntype == "cho_metadata":
            color = get_metadata_color(MetadataType.CHO.value, node_data[node]["field"])
        elif ntype == "cho":
            color = "#66c2a5"
        else:
            color = "grey"

        if ntype == "memory" and state.current_memory == node_data[node]:
            color = "#1f77b4"

        if ntype == "cho":
            size = 1400
        elif ntype == "memory":
            size = 1000
        else:
            size = 600

        shape = "o"
        if ntype == "memory":
            shape = "s"
        elif ntype == "memory_metadata":
            shape = "D"
        elif ntype == "cho_metadata":
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
    # EDGES (CURVED & CLEAR)
    # =========================
    for u, v in G.edges:

        if "memory_metadata" in u or "memory_metadata" in v:
            color = "#2ca02c"
            rad = 0.25
        elif "cho_metadata" in u or "cho_metadata" in v:
            color = "#1f77b4"
            rad = -0.25
        elif ("memory:" in u and "CHO:" in v) or ("CHO:" in u and "memory:" in v):
            color = "#ff7f0e"
            rad = 0.1
        else:
            color = "#cccccc"
            rad = 0.05

        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=[(u, v)],
            edge_color=color,
            width=1.6,
            alpha=0.65,
            connectionstyle=f"arc3,rad={rad}",
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
        elif ntype in ["memory_metadata", "cho_metadata"]:
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
        Line2D([0], [0], marker='D', color='w', label='Memory Metadata',
               markerfacecolor='#a1d99b', markersize=10),
        Line2D([0], [0], marker='h', color='w', label='CHO Metadata',
               markerfacecolor='#ffcc66', markersize=10),
    ]

    ax.legend(handles=legend_elements)

    title = f"Memory View: {state.current_memory.custom_id}" \
        if state.current_memory else f"CHO View: {state.current_cho}"

    ax.set_title(title)
    ax.margins(0.2)

    # =========================
    # CLICK INTERACTION
    # =========================
    def on_click(event):
        if event.xdata is None or event.ydata is None:
            return

        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.08 and abs(event.ydata - y) < 0.08:

                if node.startswith("CHO:"):
                    state.current_cho = node_data[node]
                    state.current_memory = None
                    generate_graph(state.graph_frame, state)

                elif node.startswith("memory:"):
                    state.current_memory = node_data[node]
                    state.current_cho = None
                    generate_graph(state.graph_frame, state)

                else:
                    md = node_data[node]
                    messagebox.showinfo(
                        "Metadata",
                        f"{md['field']}\nValue: {md['value']}"
                    )
                break

    fig.canvas.mpl_connect("button_press_event", on_click)

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    state.canvas = canvas
