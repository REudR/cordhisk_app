import tkinter as tk
<<<<<<< HEAD
=======
from tkinter import ttk
>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f

from state import AppState
from ui.editor import Editor
from ui.cho_panel import CHOPanel
from ui.memory_panel import MemoryPanel
from ui.metadata_panel import MetadataPanel

<<<<<<< HEAD
=======
from features.graph import generate_graph
>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f
from features.compare import compare
from features.search import search
from features.rdf_export import export_cho_rdf, export_memory_rdf

# =========================
# ROOT + STATE
# =========================
root = tk.Tk()
<<<<<<< HEAD
root.title("CORDHISK - Community-Driven Cultural Heritage Metadata Manager - Rafael Ramirez Eudave, TU Delft, 2026")
=======
root.title("CORDHISK")
>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f
root.geometry("1600x800")

state = AppState()

# =========================
<<<<<<< HEAD
# MAIN HORIZONTAL LAYOUT
# =========================
main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashwidth=4)
main_pane.pack(fill="both", expand=True)

# =========================
# SIDEBAR (LEFT + MIDDLE)
# =========================
sidebar = tk.Frame(main_pane)   # ✅ NO fixed width here!
main_pane.add(sidebar)

# ✅ Prevent sidebar from stretching
main_pane.paneconfig(sidebar, stretch="never")

# --- LEFT PANEL ---
left = tk.Frame(sidebar, width=260)
left.pack(side="left", fill="y")
left.pack_propagate(False)

# --- MIDDLE PANEL ---
middle = tk.Frame(sidebar, width=220)
middle.pack(side="left", fill="y")
middle.pack_propagate(False)

# =========================
# RIGHT SIDE (EDITOR + GRAPH)
# =========================
right_container = tk.PanedWindow(main_pane, orient=tk.HORIZONTAL, sashwidth=4)
main_pane.add(right_container)

# ✅ Only this pane expands
main_pane.paneconfig(right_container, stretch="always")

right = tk.Frame(right_container)
graph_frame = tk.Frame(right_container)

right_container.add(right)
right_container.add(graph_frame)

right_container.paneconfig(right, minsize=250)
right_container.paneconfig(graph_frame, minsize=650)

=======
# LAYOUT FRAMES
# =========================
# =========================
# LEFT + MIDDLE (fixed)
# =========================
left = tk.Frame(root)
left.pack(side="left", fill="y")

middle = tk.Frame(root)
middle.pack(side="left", fill="y")

# =========================
# MAIN SPLIT (resizable)
# =========================
main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL)
main_pane.pack(fill="both", expand=True)

# -------------------------
# EDITOR + METADATA PANEL
# -------------------------
right = tk.Frame(main_pane)
main_pane.add(right)

# -------------------------
# GRAPH PANEL
# -------------------------
graph_frame = tk.Frame(main_pane)
main_pane.add(graph_frame)

main_pane.paneconfig(right, minsize=400)
main_pane.paneconfig(graph_frame, minsize=300)
>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f
state.graph_frame = graph_frame

# =========================
# MAIN UI COMPONENTS
# =========================
<<<<<<< HEAD
editor = Editor(right, state)

=======

editor = Editor(right, state)

# Panels

>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f
cho_panel = CHOPanel(left, state, None)
memory_panel = MemoryPanel(middle, editor, state)

metadata_panel = MetadataPanel(right, state, editor)
state.metadata_panel = metadata_panel

# =========================
<<<<<<< HEAD
# BUTTON BAR (2 ROWS ✅)
=======
# BUTTON BAR (2 ROWS)
>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f
# =========================
bar = tk.Frame(right)
bar.pack(fill="x", pady=5)

<<<<<<< HEAD
# -------- Row 1: Editing --------
=======
# ---- Row 1 (editing tools) ----
>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f
row1 = tk.Frame(bar)
row1.pack(fill="x")

tk.Button(row1, text="Save", command=editor.save).pack(side="left", padx=3)
<<<<<<< HEAD
tk.Button(row1, text="Tag", command=metadata_panel.open_add_dialog).pack(side="left", padx=3)
tk.Button(row1, text="Untag", command=metadata_panel.delete).pack(side="left", padx=3)

# -------- Row 2: Analysis / Export --------
row2 = tk.Frame(bar)
row2.pack(fill="x")

tk.Button(row2, text="Compare", command=lambda: compare(state.current_cho)).pack(side="left", padx=3)
tk.Button(row2, text="Search", command=search).pack(side="left", padx=3)
tk.Button(row2, text="CHO RDF", command=lambda: export_cho_rdf(state.current_cho)).pack(side="left", padx=3)
tk.Button(row2, text="Mem. RDF", command=lambda: export_memory_rdf(state.current_memory)).pack(side="left", padx=3)

=======

tk.Button(
    row1,
    text="Tag",
    command=metadata_panel.open_add_dialog
).pack(side="left", padx=3)

tk.Button(
    row1,
    text="Untag",
    command=metadata_panel.delete
).pack(side="left", padx=3)

# ---- Row 2 (analysis tools) ----
#row1 = tk.Frame(bar)
#
row1.pack(fill="x")

#tk.Button(
#    row2,
#    text="Generate Graph",
#    command=lambda: generate_graph(graph_frame, state)
#).pack(side="left", padx=3)

tk.Button(
    row1,
    text="Compare",
    command=lambda: compare(state.current_cho)
).pack(side="left", padx=3)

tk.Button(row1, text="Search", command=search).pack(side="left", padx=3)

tk.Button(
    row1,
    text="CHO RDF",
    command=lambda: export_cho_rdf(state.current_cho)
).pack(side="left", padx=3)

tk.Button(
    row1,
    text="Mem. RDF",
    command=lambda: export_memory_rdf(state.current_memory)
).pack(side="left", padx=3)
>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f

# =========================
# INIT
# =========================
<<<<<<< HEAD
cho_panel.load()
memory_panel.load()

# =========================
# RUN
# =========================
root.mainloop()
=======

cho_panel.load()
memory_panel.load()
root.mainloop()
>>>>>>> 38a35e4f1c25d7c94fa7bf322f1008316931d93f
