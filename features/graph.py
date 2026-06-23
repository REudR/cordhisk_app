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
    """Color nodes based on metadata type and field"""
    if metadata_type == MetadataType.MEMORY.value:
        # Memory-intrinsic metadata (WebResource)
        return "#a1d99b"
    else:
        # CHO-linked metadata
        if field.startswith("dc:") or field.startswith("dcterms:"):
            return "#ffcc66"  # CHO (Dublin Core)
        elif field.startswith("oaf:") or field.startswith("rdaGr2:"):
            return "#66b3ff"  # Agent
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
    node_types = {}  # memory, memory_metadata, cho, cho_metadata, tag
    node_data = {}

    # =========================
    # BUILD GRAPH
    # =========================
    if state.current_memory:
        m = state.current_memory

        for md in extract_metadata(m.text):
            mn = f"memory:{m.custom_id}"
            
            # ✅ SEPARATE HANDLING BY METADATA TYPE
            if md.get("type") == MetadataType.MEMORY.value:
                # Memory-intrinsic metadata: attach directly to Memory
                mmd_node = f"memory_metadata:{m.custom_id}:{md['field']}"
                G.add_edge(mn, mmd_node)
                
                node_types[mn] = "memory"
                node_types[mmd_node] = "memory_metadata"
                
                node_data[mn] = m
                node_data[mmd_node] = md
            
            else:
                # CHO-linked metadata: full chain Memory → CHO → Metadata
                cn = f"CHO:{md['cho']}"
                cmd_node = f"cho_metadata:{md['cho']}:{md['field']}"
                
                G.add_edges_from([(mn, cn), (cn, cmd_node)])
                
                node_types[mn] = "memory"
                node_types[cn] = "cho"
                node_types[cmd_node] = "cho_metadata"
                
                node_data[mn] = m
                node_data[cn] = md["cho"]
                node_data[cmd_node] = md

    else:
        cid = state.current_cho

        for m in session.query(Memory):
            for md in extract_metadata(m.text):
                if md.get("type") == MetadataType.MEMORY.value:
                    # Skip memory-intrinsic metadata in CHO view
                    continue
                
                if md.get("cho") != cid:
                    continue

                mn = f"memory:{m.custom_id}"
                cn = f"CHO:{cid}"
                cmd_node = f"cho_metadata:{cid}:{md['field']}"

                G.add_edges_from([(mn, cn), (cn, cmd_node)])

                node_types[mn] = "memory"
                node_types[cn] = "cho"
                node_types[cmd_node] = "cho_metadata"

                node_data[mn] = m
                node_data[cn] = cid
                node_data[cmd_node] = md

    if not G.nodes:
        messagebox.showinfo("Info", "No data to display")
        return

    # =========================
    # CLUSTER LAYOUT
    # =========================
    pos = {}
    offset = 0
    groups = {}

    # Group by memory or cho
    for n in G.nodes:
        if node_types[n] == "memory":
            gid = f"mem:{node_data[n].custom_id}"
        elif node_types[n] == "memory_metadata":
            gid = f"mem:{node_data[n]['field'].split(':')[0]}"  # Group by field category
        elif node_types[n] == "cho":
            gid = f"cho:{node_data[n]}"
        elif node_types[n] == "cho_metadata":
            gid = f"cho:{node_data[n]['cho']}"
        else:
            gid = "other"
        
        groups.setdefault(gid, []).append(n)

    for _, nodes in groups.items():
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
        elif ntype == "memory_metadata":
            color = "#a1d99b"  # Green for memory metadata
        elif ntype == "cho_metadata":
            color = get_metadata_color(MetadataType.CHO.value, node_data[node]["field"])
        elif ntype == "cho":
            color = "#66c2a5"
        else:
            color = "grey"

        # Highlight selected memory
        if ntype == "memory" and state.current_memory == node_data[node]:
            color = "#1f77b4"

        # SIZE
        if ntype == "cho":
            size = 1400
        elif ntype == "memory":
            size = 1000
        elif ntype == "memory_metadata" or ntype == "cho_metadata":
            size = 600
        else:
            size = 700

        # SHAPE
        shape = "o"
        if ntype == "memory":
            shape = "s"  # square
        elif ntype == "memory_metadata":
            shape = "D"  # diamond for memory metadata
        elif ntype == "cho_metadata":
            shape = "h"  # hexagon for cho metadata

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
        # Memory to memory_metadata
        if ("memory_metadata:" in u or "memory_metadata:" in v):
            edge_colors.append("#2ca02c")  # Dark green for memory attachment
        # Memory to CHO
        elif ("memory:" in u and "CHO:" in v) or ("CHO:" in u and "memory:" in v):
            edge_colors.append("#ff7f0e")  # Orange for memory-cho link
        # CHO to cho_metadata
        elif ("cho_metadata:" in u or "cho_metadata:" in v):
            edge_colors.append("#1f77b4")  # Dark blue for cho attachment
        else:
            edge_colors.append("#cccccc")  # Default grey
    
    nx.draw_networkx_edges(
        G,
        pos,
        width=2,
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
        elif ntype == "memory_metadata":
            labels[node] = data["field"].split(":")[-1]
        elif ntype == "cho_metadata":
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

        Line2D([0], [0], marker='h', color='w', label='Agent Metadata',
               markerfacecolor='#66b3ff', markersize=10),
    ]

    ax.legend(handles=legend_elements)

    # =========================
    # CONTEXT TITLE
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
                # METADATA CLICK (Memory or CHO)
                # =========================
                else:
                    from tkinter import messagebox
    
                    md = node_data[node]
                    md_type = md.get("type", "unknown")
                    
                    if md_type == MetadataType.MEMORY.value:
                        msg = f"[Memory Metadata]\n{md['field']}\nValue: {md['value']}"
                    else:
                        msg = f"[CHO Metadata]\n{md['field']}\nValue: {md['value']}\nCHO: {md.get('cho', 'N/A')}"
                    
                    messagebox.showinfo("Metadata", msg)
    
                break

    fig.canvas.mpl_connect("button_press_event", on_click)

    # =========================
    # EMBED IN TK
    # =========================
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    state.canvas = canvas
