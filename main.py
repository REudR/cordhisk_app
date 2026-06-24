import tkinter as tk

from state import AppState
from ui.editor import Editor
from ui.cho_panel import CHOPanel
from ui.memory_panel import MemoryPanel
from ui.metadata_panel import MetadataPanel

from features.compare import compare
from features.search import search
from features.rdf_export import export_cho_rdf, export_memory_rdf

# =========================
# ROOT + STATE
# =========================
root = tk.Tk()
root.title("CORDHISK - Community-Driven Cultural Heritage Metadata Manager - Rafael Ramirez Eudave, TU Delft, 2026")
root.geometry("1600x800")

state = AppState()

# =========================
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

state.graph_frame = graph_frame

# =========================
# MAIN UI COMPONENTS
# =========================
editor = Editor(right, state)

cho_panel = CHOPanel(left, state, None)
memory_panel = MemoryPanel(middle, editor, state)
state.memory_panel = memory_panel

metadata_panel = MetadataPanel(right, state, editor)
state.metadata_panel = metadata_panel

# =========================
# BUTTON BAR (2 ROWS ✅)
# =========================
bar = tk.Frame(right)
bar.pack(fill="x", pady=5)

# -------- Row 1: Editing --------
row1 = tk.Frame(bar)
row1.pack(fill="x")

#tk.Button(row1, text="Save", command=editor.save).pack(side="left", padx=3)
#tk.Button(row1, text="Tag", command=metadata_panel.open_add_cho_dialog).pack(side="left", padx=3)
#tk.Button(row1, text="Untag", command=metadata_panel.delete).pack(side="left", padx=3)
tk.Button(row1, text="Compare", command=lambda: compare(state.current_cho)).pack(side="left", padx=3)
tk.Button(row1, text="Search", command=search).pack(side="left", padx=3)
tk.Button(row1, text="CHO RDF", command=lambda: export_cho_rdf(state.current_cho)).pack(side="left", padx=3)
tk.Button(row1, text="Mem. RDF", command=lambda: export_memory_rdf(state.current_memory)).pack(side="left", padx=3)

# =========================
# INIT
# =========================
cho_panel.load()
memory_panel.load()

# =========================
# RUN
# =========================
root.mainloop()
