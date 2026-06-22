import networkx as nx
import matplotlib.pyplot as plt
import random
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from db import session, Memory, CHO
from services.metadata import extract_metadata, get_memory_title
from features.tree_views import show_cho_tree, show_memory_tree


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
# MAIN GRAPH FUNCTION
# =========================
def generate_graph(frame, state):
    from tkinter import messagebox

    # =========================
    # VALIDATION
    # =========================
    if not state.current_cho and not state.current_memory:
        messagebox.showinfo("Info", "Select CHO or Memory first")
        return

    # =========================
    # CLEAR PREVIOUS GRAPH
    # =========================
    if state.canvas:
        state.canvas.get_tk_widget().destroy()
        state.canvas = None

    # =========================
    # INITIALIZE GRAPH
    # =========================
    G = nx.Graph()
    node_types = {}
    node_data = {}

    # =========================
    # BUILD GRAPH
    # =========================
    if state.current_memory:
        # 🔵 Priority: memory graph
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
    
    elif state.current_cho:
        # 🟢 fallback: CHO graph
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

    # =========================
    # SAFETY CHECK
    # =========================
    if not G.nodes:
        messagebox.showinfo("Info", "No data to display")
        return

    # =========================
    # COLOR PER CHO (FIXED POSITION)
    # =========================
    all_chos = list({
        node_data[n] for n in G.nodes
        if node_types.get(n) == "cho"
    })

    cho_colors = get_cho_color_map(all_chos)

    # =========================
    # DRAW GRAPH
    # =========================
    fig = plt.Figure()
    ax = fig.add_subplot(111)

    pos = nx.spring_layout(G)

    # Draw nodes individually with colors
    for node in G.nodes:
        ntype = node_types.get(node)

        if ntype == "memory":
            color = "lightblue"
            shape = "s"

        elif ntype == "tag":
            color = "orange"
            shape = "h"

        elif ntype == "cho":
            color = cho_colors.get(node_data[node], "lightgreen")
            shape = "o"

        else:
            color = "grey"
            shape = "o"

        nx.draw_networkx_nodes(
            G, pos,
            nodelist=[node],
            node_color=color,
            node_shape=shape,
            node_size=800,
            ax=ax
        )

    # Draw edges
    nx.draw_networkx_edges(G, pos, ax=ax)

    # =========================
    # LABELS
    # =========================
    labels = {}

    for node in G.nodes:
        ntype = node_types.get(node)
        data = node_data.get(node)

        if ntype == "memory":
            labels[node] = get_memory_title(data.text, data.custom_id)

        elif ntype == "tag":
            labels[node] = data["value"]

        elif ntype == "cho":
            cho_obj = session.query(CHO).filter_by(custom_id=data).first()
            labels[node] = cho_obj.title if cho_obj else data

    nx.draw_networkx_labels(
        G, pos,
        labels=labels,
        font_size=6,
        ax=ax
    )

    # =========================
    # CLICK INTERACTION
    # =========================
    def on_click(event):
        if event.xdata is None or event.ydata is None:
            return

        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:

                if node.startswith("CHO:"):
                    show_cho_tree(node_data[node])

                elif node.startswith("memory:"):
                    state.current_memory = node_data[node]
                    messagebox.showinfo(
                        "Memory",
                        f"Selected {node_data[node].custom_id}"
                    )

                else:
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
