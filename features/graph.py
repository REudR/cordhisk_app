import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Patch
from tkinter import messagebox, Frame

from db import session, Memory, CHO
from services.metadata import extract_metadata, get_memory_title
from services.types import MetadataType


# =========================
# COLOR LOGIC
# =========================
def get_metadata_color(field):
    if field.startswith("dc:") or field.startswith("dcterms:"):
        return "#ffcc66"
    elif field.startswith("oaf:") or field.startswith("rdaGr2:"):
        return "#66b3ff"
    return "#cccccc"


# =========================
# NODE STYLE
# =========================
def get_node_style(node, node_types, node_data, state):
    t = node_types[node]

    if t == "memory":
        mem_id = node.split(":")[1]
        expanded = mem_id in state.expanded_memories
        return (
            "#3182bd" if expanded else "#9ecae1",
            "s",
            1200,
            "black" if not expanded else "none"
        )

    if t == "cho":
        return "#66c2a5", "o", 1800, "none"

    if t == "memory_metadata":
        return "#a1d99b", "h", 500, "none"

    if t == "cho_metadata":
        field = node_data[node].get("field", "")
        return get_metadata_color(field), "h", 500, "none"

    return "grey", "o", 500, "none"


# =========================
# LABEL BUILDER ✅ NEW CLEAN
# =========================
def build_labels(G, node_types, node_data, node_counts, cho_cache):
    labels = {}

    def wrap_text(text, max_len=18):
        words = text.split()
        lines = []
        current = ""

        for w in words:
            if len(current) + len(w) + 1 > max_len:
                lines.append(current)
                current = w
            else:
                current = f"{current} {w}".strip()

        if current:
            lines.append(current)

        return "\n".join(lines)

    for node in G.nodes:
        t = node_types[node]
        d = node_data[node]

        if t == "memory":
            mem_id = d.custom_id
            title = get_memory_title(d.text, d.custom_id)
            labels[node] = f"{mem_id}\n{wrap_text(title)}"

        elif t == "cho":
            cid = d
            title = cho_cache.get(cid, str(cid))
            labels[node] = f"{cid}\n{wrap_text(title)}"

        else:
            field = d.get("field", "").split(":")[-1]
            count = node_counts.get(node, 0)
            labels[node] = f"{field} ({count})" if count > 1 else field

    return labels


# =========================
# MAIN GRAPH
# =========================
def generate_graph(frame, state):

    state.expanded_memories = getattr(state, "expanded_memories", set())
    state.show_memory_metadata = getattr(state, "show_memory_metadata", True)

    if not state.current_cho and not state.current_memory:
        messagebox.showinfo("Info", "Select CHO or Memory first")
        return

    if getattr(state, "control_frame", None):
        state.control_frame.destroy()

    if getattr(state, "canvas", None):
        state.canvas.get_tk_widget().destroy()

    if getattr(state, "toolbar", None):
        state.toolbar.destroy()

    G = nx.Graph()
    node_types = {}
    node_data = {}
    node_counts = defaultdict(int)

    cho_cache = {c.custom_id: c.title for c in session.query(CHO)}

    def add_node(n, ntype, data):
        if n not in node_types:
            G.add_node(n)
            node_types[n] = ntype
            node_data[n] = data

    def add_metadata(mn, metadata):
        for md in metadata:
            key = f"{md.get('field')}::{md.get('value')}"

            if md.get("type") == MetadataType.MEMORY.value:

                if not state.show_memory_metadata:
                    continue

                mem_id = mn.split(":")[1]
                if mem_id not in state.expanded_memories:
                    continue

                node = f"memory_metadata:{key}"
                G.add_edge(mn, node)

                add_node(node, "memory_metadata", md)
                node_counts[node] += 1

            elif md.get("type") == MetadataType.CHO.value:

                cho_id = md.get("cho")
                if not cho_id:
                    continue

                cn = f"CHO:{cho_id}"
                node = f"cho_metadata:{key}"

                G.add_edges_from([(mn, node), (node, cn)])

                add_node(node, "cho_metadata", md)
                add_node(cn, "cho", cho_id)

                node_counts[node] += 1

    # MEMORY VIEW
    if state.current_memory:
        m = state.current_memory
        mn = f"memory:{m.custom_id}"

        add_node(mn, "memory", m)
        add_metadata(mn, extract_metadata(m.text))

    # CHO VIEW
    else:
        cid = state.current_cho
        cn = f"CHO:{cid}"

        add_node(cn, "cho", cid)

        for m in session.query(Memory):
            md_list = extract_metadata(m.text)

            cho_md = [md for md in md_list if md.get("cho") == cid]
            memory_md = [md for md in md_list if md.get("type") == MetadataType.MEMORY.value]

            if not cho_md:
                continue

            mn = f"memory:{m.custom_id}"
            add_node(mn, "memory", m)

            add_metadata(mn, cho_md)

            if state.show_memory_metadata and str(m.custom_id) in state.expanded_memories:
                add_metadata(mn, memory_md)

    if not G.nodes:
        messagebox.showinfo("Info", "No data to display")
        return

    # LAYOUT
    pos = {}
    layers = {"memory": [], "metadata": [], "cho": []}

    for node in G.nodes:
        t = node_types[node]
        if t == "memory":
            layers["memory"].append(node)
        elif t == "cho":
            layers["cho"].append(node)
        else:
            layers["metadata"].append(node)

    def distribute(nodes, x):
        n = len(nodes)
        for i, node in enumerate(nodes):
            pos[node] = (x, (i - n / 2))

    distribute(layers["memory"], -2)
    distribute(layers["metadata"], 0)
    distribute(layers["cho"], 2)

    # DRAW
    fig = plt.Figure(figsize=(14, 9))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    ax = fig.add_subplot(111)
    ax.set_axis_off()

    for node in G.nodes:
        color, shape, size, edge = get_node_style(node, node_types, node_data, state)

        nx.draw_networkx_nodes(
            G, pos,
            nodelist=[node],
            node_color=color,
            node_shape=shape,
            node_size=size,
            edgecolors=edge,
            linewidths=1.5,
            alpha=0.9 if node_types[node] in ["memory", "cho"] else 0.7,
            ax=ax
        )

    nx.draw_networkx_edges(G, pos, width=1.2, alpha=0.5, ax=ax)

    # ✅ LABELS (clean + working)
    labels = build_labels(G, node_types, node_data, node_counts, cho_cache)

    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, ax=ax)

    # LEGEND
    legend_elements = [
        Patch(facecolor="#3182bd", label="Memory (expanded)"),
        Patch(facecolor="#9ecae1", edgecolor="black", label="Memory (collapsed)"),
        Patch(facecolor="#66c2a5", label="CHO"),
        Patch(facecolor="#a1d99b", label="Memory Metadata"),
        Patch(facecolor="#ffcc66", label="CHO Metadata"),
        Patch(facecolor="#66b3ff", label="Agent Metadata"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")

    ax.set_title(
        f"Memory View: {state.current_memory.custom_id}"
        if state.current_memory else f"CHO View: {state.current_cho}"
    )

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    state.canvas = canvas

    hidden_toolbar = NavigationToolbar2Tk(canvas, frame)
    hidden_toolbar.pack_forget()
    canvas.toolbar = hidden_toolbar
    state.hidden_toolbar = hidden_toolbar

    control_frame = Frame(frame)
    control_frame.pack(fill="x")
    state.control_frame = control_frame

    # CLICK
    def on_click(event):
        if event.xdata is None:
            return

        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:
                if event.button == 1 and node_types[node] == "memory":
                    mem_id = node.split(":")[1]

                    if mem_id in state.expanded_memories:
                        state.expanded_memories.remove(mem_id)
                    else:
                        state.expanded_memories.add(mem_id)

                    generate_graph(frame, state)
                    return

    fig.canvas.mpl_connect("button_press_event", on_click)

    # =========================
    # TOOLTIP ✅ RESTORED
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
            tooltip.set_visible(False)
            fig.canvas.draw_idle()
            return

        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:

                # ✅ ONLY metadata nodes show tooltip
                if node_types[node] in ["memory_metadata", "cho_metadata"]:
                    data = node_data[node]

                    tooltip.xy = (x, y)
                    tooltip.set_text(
                        f"{data.get('field')}\n{data.get('value')}"
                    )
                    tooltip.set_visible(True)
                    fig.canvas.draw_idle()
                    return

        # ✅ hide tooltip if nothing matched
        tooltip.set_visible(False)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_move)
