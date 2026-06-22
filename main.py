import tkinter as tk
from tkinter import ttk

from state import AppState
from ui.editor import Editor
from ui.cho_panel import CHOPanel
from ui.memory_panel import MemoryPanel
from ui.metadata_panel import MetadataPanel

from features.graph import generate_graph
from features.compare import compare
from features.search import search
from features.rdf_export import export_cho_rdf, export_memory_rdf

# =========================
# ROOT + STATE
# =========================
root = tk.Tk()
root.title("CORDHISK")
root.geometry("1600x800")

state = AppState()

# =========================
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
state.graph_frame = graph_frame

# =========================
# MAIN UI COMPONENTS
# =========================

editor = Editor(right, state)

# Panels

cho_panel = CHOPanel(left, state, None)
memory_panel = MemoryPanel(middle, editor, state)

metadata_panel = MetadataPanel(right, state, editor)
state.metadata_panel = metadata_panel

# =========================
# BUTTON BAR (2 ROWS)
# =========================
bar = tk.Frame(right)
bar.pack(fill="x", pady=5)

# ---- Row 1 (editing tools) ----
row1 = tk.Frame(bar)
row1.pack(fill="x")

tk.Button(row1, text="Save", command=editor.save).pack(side="left", padx=3)

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

# =========================
# INIT
# =========================

cho_panel.load()
memory_panel.load()
root.mainloop()