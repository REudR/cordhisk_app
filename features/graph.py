import networkx as nx
import matplotlib.pyplot as plt
import random
from collections import defaultdict
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Patch
from tkinter import messagebox

from db import session, Memory, CHO
from services.metadata import extract_metadata, get_memory_title
from utils import MetadataType



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

    if not hasattr(state, "expanded_memories"):
        state.expanded_memories = set()

    if not hasattr(state, "show_memory_metadata"):
        state.show_memory_metadata = True

    if not state.current_cho and not state.current_memory:
        messagebox.showinfo("Info", "Select CHO or Memory first")
        return
    
    # =========================
    # CLEANUP (FIXED)
    # =========================
    if state.canvas:
        state.canvas.get_tk_widget().destroy()
        state.canvas = None

    if hasattr(state, "toolbar") and state.toolbar:
        state.toolbar.destroy()
        state.toolbar = None

    G = nx.Graph()
    node_types = {}
    node_data = {}
    node_counts = defaultdict(int)

    # =========================
    # MEMORY VIEW
    # =========================
    if state.current_memory:
        m = state.current_memory
        mn = f"memory:{m.custom_id}"

        G.add_node(mn)
        node_types[mn] = "memory"
        node_data[mn] = m

        for md in extract_metadata(m.text):

            key = f"{md.get('field')}::{md.get('value')}"

            if md.get("type") == MetadataType.MEMORY.value:

                if not state.show_memory_metadata:
                    continue

                if str(m.custom_id) not in state.expanded_memories:
                    continue

                mmd_node = f"memory_metadata:{key}"

                G.add_edge(mn, mmd_node)
                node_types[mmd_node] = "memory_metadata"
                node_data[mmd_node] = md
                node_counts[mmd_node] += 1

            else:
                cn = f"CHO:{md.get('cho')}"
                cmd_node = f"cho_metadata:{key}"

                G.add_edges_from([(mn, cmd_node), (cmd_node, cn)])

                node_types[cn] = "cho"
                node_data[cn] = md.get("cho")

                node_types[cmd_node] = "cho_metadata"
                node_data[cmd_node] = md
                node_counts[cmd_node] += 1

    # =========================
    # CHO VIEW
    # =========================
    else:
        cid = state.current_cho
        cn = f"CHO:{cid}"

        G.add_node(cn)
        node_types[cn] = "cho"
        node_data[cn] = cid

        for m in session.query(Memory):

            memory_connected = False
            memory_md = []
            cho_md = []

            for md in extract_metadata(m.text):
                if md.get("type") == MetadataType.MEMORY.value:
                    memory_md.append(md)
                elif md.get("cho") == cid:
                    memory_connected = True
                    cho_md.append(md)

            if not memory_connected:
                continue

            mn = f"memory:{m.custom_id}"

            G.add_node(mn)
            node_types[mn] = "memory"
            node_data[mn] = m

            for md in cho_md:
                key = f"{md.get('field')}::{md.get('value')}"
                cmd_node = f"cho_metadata:{key}"

                G.add_edges_from([(mn, cmd_node), (cmd_node, cn)])

                node_types[cmd_node] = "cho_metadata"
                node_data[cmd_node] = md
                node_counts[cmd_node] += 1

            for md in memory_md:
                if not state.show_memory_metadata:
                    continue

                if str(m.custom_id) not in state.expanded_memories:
                    continue

                key = f"{md.get('field')}::{md.get('value')}"
                mmd_node = f"memory_metadata:{key}"

                G.add_edge(mn, mmd_node)
                node_types[mmd_node] = "memory_metadata"
                node_data[mmd_node] = md
                node_counts[mmd_node] += 1

    if not G.nodes:
        messagebox.showinfo("Info", "No data to display")
        return

    # =========================
    # LAYOUT
    # =========================

    pos = nx.spring_layout(G, k=1.8, iterations=150, seed=42)
    
    # ✅ group nodes by type
    layers = {
        "memory": [],
        "metadata": [],
        "cho": []
    }
    
    for node in G.nodes:
        ntype = node_types[node]
    
        if ntype == "memory":
            layers["memory"].append(node)
        elif ntype in ["memory_metadata", "cho_metadata"]:
            layers["metadata"].append(node)
        elif ntype == "cho":
            layers["cho"].append(node)
    
    # ✅ assign positions with spacing
    def distribute(nodes, x_pos):
        n = len(nodes)
        if n == 0:
            return
    
        spacing = 4 / max(n, 1)  # controls vertical distance
    
        for i, node in enumerate(nodes):
            y = (i - n / 2) * spacing
            pos[node] = (
                x_pos + random.uniform(-0.05, 0.05),
                y + random.uniform(-0.05, 0.05)
            )
    
    # ✅ apply layers
    distribute(layers["memory"], -2)
    distribute(layers["metadata"], 0)
    distribute(layers["cho"], 2)

    # =========================
    # DRAW
    # =========================
    fig = plt.Figure()
    ax = fig.add_subplot(111)

    for node in G.nodes:
        ntype = node_types[node]

        edgecolor = "none"

        if ntype == "memory":
            mem_id = node.split(":")[1]
            expanded = mem_id in state.expanded_memories
            color = "#3182bd" if expanded else "#9ecae1"

            if not expanded:
                edgecolor = "black"

        elif ntype == "memory_metadata":
            color = "#a1d99b"
        elif ntype == "cho_metadata":
            color = get_metadata_color(
                MetadataType.CHO.value,
                node_data[node].get("field", "")
            )
        elif ntype == "cho":
            color = "#66c2a5"
        else:
            color = "grey"

        size = 1800 if ntype == "cho" else 1200 if ntype == "memory" else 500

        shape = "o"
        if ntype == "memory":
            shape = "s"
        elif ntype in ["memory_metadata", "cho_metadata"]:
            shape = "h"

        nx.draw_networkx_nodes(
            G, pos,
            nodelist=[node],
            node_color=color,
            node_shape=shape,
            node_size=size,
            edgecolors=edgecolor,
            linewidths=1.5,
            alpha=0.9 if ntype in ["cho", "memory"] else 0.7,
            ax=ax
        )

    nx.draw_networkx_edges(G, pos, width=1.2, alpha=0.5, ax=ax)

    # =========================
    # LEGEND
    # =========================
    legend_elements = [
        Patch(facecolor="#3182bd", label="Memory (expanded)"),
        Patch(facecolor="#9ecae1", edgecolor="black", label="Memory (collapsed)"),
        Patch(facecolor="#66c2a5", label="CHO"),
        Patch(facecolor="#a1d99b", label="Memory Metadata"),
        Patch(facecolor="#ffcc66", label="DC Metadata"),
        Patch(facecolor="#66b3ff", label="Agent/RDA Metadata"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")

    # =========================
    # LABELS
    # =========================
    labels = {}
    for node in G.nodes:
        ntype = node_types[node]
        data = node_data.get(node, {})

        if ntype == "memory":
            labels[node] = get_memory_title(data.text, data.custom_id)

        elif ntype in ["memory_metadata", "cho_metadata"]:
            field = data.get("field", "").split(":")[-1]
            count = node_counts[node]
            labels[node] = f"{field} ({count})" if count > 1 else field

        elif ntype == "cho":
            cho_obj = session.query(CHO).filter_by(custom_id=data).first()
            labels[node] = cho_obj.title if cho_obj else str(data)

    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, ax=ax)

    # =========================
    # FINALIZE + TOOLBAR
    # =========================
    ax.set_title(
        f"Memory View: {state.current_memory.custom_id}"
        if state.current_memory else f"CHO View: {state.current_cho}"
    )

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    # ✅ toolbar (FIXED: no duplication)
    toolbar = NavigationToolbar2Tk(canvas, frame)
    toolbar.update()
    state.toolbar = toolbar

    state.canvas = canvas

        # =========================
    # CLICK HANDLER
    # =========================
    def on_click(event):
        if event.xdata is None:
            return
    
        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:
    
                if event.button == 1:  # LEFT CLICK
                    if node_types[node] == "memory":
                        mem_id = node.split(":")[1]
    
                        if mem_id in state.expanded_memories:
                            state.expanded_memories.remove(mem_id)
                        else:
                            state.expanded_memories.add(mem_id)
    
                        generate_graph(frame, state)
                        return
    
                elif event.button == 3:  # RIGHT CLICK
                    print(f"Right-click on {node}")
    
    fig.canvas.mpl_connect("button_press_event", on_click)
    
    
    # =========================
    # TOOLTIP
    # =========================
    tooltip = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(10, 10),
        textcoords="offset points",
        bbox=dict(boxstyle="round", fc="w"),
    )
    tooltip.set_visible(False)
    
    def on_move(event):
        if event.xdata is None:
            return
    
        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:
                if node_types[node] in ["memory_metadata", "cho_metadata"]:
                    data = node_data[node]
                    tooltip.xy = (x, y)
                    tooltip.set_text(f"{data.get('field')}\n{data.get('value')}")
                    tooltip.set_visible(True)
                    fig.canvas.draw_idle()
                    return
    
        tooltip.set_visible(False)
        fig.canvas.draw_idle()
    
    fig.canvas.mpl_connect("motion_notify_event", on_move)