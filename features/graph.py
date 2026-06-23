import networkx as nx
import matplotlib.pyplot as plt
import random
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
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
    # MEMORY VIEW
    # =========================
    if state.current_memory:
        m = state.current_memory
        mn = f"memory:{m.custom_id}"

        node_types[mn] = "memory"
        node_data[mn] = m

        for md in extract_metadata(m.text):

            if md.get("type") == MetadataType.MEMORY.value:
                mmd_node = f"memory_metadata:{m.custom_id}:{md['field']}:{md['value']}"

                G.add_edge(mn, mmd_node)

                node_types[mmd_node] = "memory_metadata"
                node_data[mmd_node] = md

            else:
                cn = f"CHO:{md['cho']}"
                cmd_node = f"cho_metadata:{md['cho']}:{md['field']}:{md['value']}"

                G.add_edges_from([
                    (mn, cmd_node),
                    (cmd_node, cn)
                ])

                node_types[cn] = "cho"
                node_data[cn] = md["cho"]

                node_types[cmd_node] = "cho_metadata"
                node_data[cmd_node] = md

    # =========================
    # CHO VIEW
    # =========================
    else:
        cid = state.current_cho
        cn = f"CHO:{cid}"

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
            node_types[mn] = "memory"
            node_data[mn] = m

            # CHO metadata
            for md in cho_md:
                cmd_node = f"cho_metadata:{cid}:{md['field']}:{md['value']}"

                G.add_edges_from([
                    (mn, cmd_node),
                    (cmd_node, cn)
                ])

                node_types[cmd_node] = "cho_metadata"
                node_data[cmd_node] = md

            # Memory metadata
            for md in memory_md:
                mmd_node = f"memory_metadata:{m.custom_id}:{md['field']}:{md['value']}"

                G.add_edge(mn, mmd_node)

                node_types[mmd_node] = "memory_metadata"
                node_data[mmd_node] = md

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
            color = "#9ecae1"
        elif ntype == "memory_metadata":
            color = "#a1d99b"
        elif ntype == "cho_metadata":
            color = get_metadata_color(MetadataType.CHO.value, node_data[node]["field"])
        elif ntype == "cho":
            color = "#66c2a5"
        else:
            color = "grey"

        size = 1400 if ntype == "cho" else 1000 if ntype == "memory" else 600

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
    # EDGES
    # =========================
    for u, v in G.edges:

        if "memory_metadata" in u or "memory_metadata" in v:
            color = "#2ca02c"; rad = 0.25
        elif "cho_metadata" in u or "cho_metadata" in v:
            color = "#1f77b4"; rad = -0.25
        else:
            color = "#ff7f0e"; rad = 0.1

        nx.draw_networkx_edges(
            G, pos,
            edgelist=[(u, v)],
            edge_color=color,
            width=1.6,
            alpha=0.65,
            connectionstyle=f"arc3,rad={rad}",
            ax=ax
        )

    # =========================
    # LABELS (✅ FIXED)
    # =========================
    labels = {}
    for node in G.nodes:
        ntype = node_types[node]
        data = node_data[node]

        if ntype == "memory":
            labels[node] = get_memory_title(data.text, data.custom_id)

        elif ntype in ["memory_metadata", "cho_metadata"]:
            # ✅ ONLY FIELD NAME, NOT VALUE
            labels[node] = data["field"].split(":")[-1]

        elif ntype == "cho":
            cho_obj = session.query(CHO).filter_by(custom_id=data).first()
            labels[node] = cho_obj.title if cho_obj else data

    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, ax=ax)

    # =========================
    # CLICK INTERACTION (✅ NEW)
    # =========================
    def on_click(event):
        if event.xdata is None or event.ydata is None:
            return

        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.08 and abs(event.ydata - y) < 0.08:

                ntype = node_types[node]

                # CHO click
                if ntype == "cho":
                    state.current_cho = node_data[node]
                    state.current_memory = None
                    generate_graph(frame, state)

                # Memory click
                elif ntype == "memory":
                    state.current_memory = node_data[node]
                    state.current_cho = None
                    generate_graph(frame, state)

                # Metadata click ✅ SHOW FULL VALUE
                elif ntype in ["memory_metadata", "cho_metadata"]:
                    md = node_data[node]

                    if ntype == "memory_metadata":
                        msg = (
                            f"[Memory Metadata]\n\n"
                            f"Field: {md['field']}\n"
                            f"Value: {md['value']}"
                        )
                    else:
                        msg = (
                            f"[CHO Metadata]\n\n"
                            f"Field: {md['field']}\n"
                            f"Value: {md['value']}\n"
                            f"CHO: {md.get('cho', 'N/A')}"
                        )

                    messagebox.showinfo("Metadata", msg)

                break

    fig.canvas.mpl_connect("button_press_event", on_click)

    ax.set_title(
        f"Memory View: {state.current_memory.custom_id}"
        if state.current_memory else f"CHO View: {state.current_cho}"
    )

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    state.canvas = canvas