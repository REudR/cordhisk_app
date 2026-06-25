import networkx as nx
import matplotlib.pyplot as plt
import random
from collections import defaultdict
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
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

    if not state.current_cho and not state.current_memory:
        messagebox.showinfo("Info", "Select CHO or Memory first")
        return

    if state.canvas:
        state.canvas.get_tk_widget().destroy()
        state.canvas = None

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

            if md.get("type") == MetadataType.MEMORY.value or md.get("type") == MetadataType.MEMORY:

                # ✅ FIX: ensure same type (string comparison)
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

                G.add_edges_from([
                    (mn, cmd_node),
                    (cmd_node, cn)
                ])

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
                if md.get("type") == MetadataType.MEMORY.value or md.get("type") == MetadataType.MEMORY:
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

                G.add_edges_from([
                    (mn, cmd_node),
                    (cmd_node, cn)
                ])

                node_types[cmd_node] = "cho_metadata"
                node_data[cmd_node] = md
                node_counts[cmd_node] += 1

            for md in memory_md:
                # ✅ FIX: string comparison
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
    pos = nx.kamada_kawai_layout(G, scale=3)

    for k in pos:
        pos[k] = (
            pos[k][0] + random.uniform(-0.08, 0.08),
            pos[k][1] + random.uniform(-0.08, 0.08)
        )

    # =========================
    # DRAW
    # =========================
    fig = plt.Figure()
    ax = fig.add_subplot(111)

    for node in G.nodes:
        ntype = node_types[node]

        if ntype == "memory":
            mem_id = node.split(":")[1]
            color = "#3182bd" if mem_id in state.expanded_memories else "#9ecae1"
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

        size = 1400 if ntype == "cho" else 1000 if ntype == "memory" else 600

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
            ax=ax
        )

    nx.draw_networkx_edges(G, pos, width=1.6, alpha=0.6, ax=ax)

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

    # =========================
    # CLICK HANDLER
    # =========================
    def on_click(event):
        if event.xdata is None:
            return

        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:

                if node_types[node] == "memory":
                    mem_id = node.split(":")[1]  # string

                    if mem_id in state.expanded_memories:
                        state.expanded_memories.remove(mem_id)
                    else:
                        state.expanded_memories.add(mem_id)

                    generate_graph(frame, state)
                    return

    fig.canvas.mpl_connect("button_press_event", on_click)

    # =========================
    # FINALIZE
    # =========================
    ax.set_title(
        f"Memory View: {state.current_memory.custom_id}"
        if state.current_memory else f"CHO View: {state.current_cho}"
    )

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    state.canvas = canvas