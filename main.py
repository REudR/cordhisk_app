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
state.root = root
state.current_memory = None
state.current_cho = None
state.spans = []

state.highlighted_memories = set()
state.highlighted_cho = None

# =========================
# MAIN LAYOUT
# =========================
main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashwidth=4)
main_pane.pack(fill="both", expand=True)


# =========================
# SIDEBAR (25%)
# =========================
sidebar_width_ratio = 0.25

sidebar = tk.Frame(main_pane)
main_pane.add(sidebar)

# --- LEFT PANEL ---
left = tk.Frame(sidebar, width=195)
left.pack(side="left", fill="y")
left.pack_propagate(False)

# --- MIDDLE PANEL ---
middle = tk.Frame(sidebar, width=165)
middle.pack(side="left", fill="y")
middle.pack_propagate(False)


# =========================
# RIGHT SIDE
# =========================
right_container = tk.PanedWindow(main_pane, orient=tk.HORIZONTAL, sashwidth=4)
main_pane.add(right_container)

right = tk.Frame(right_container)
graph_frame = tk.Frame(right_container)

right_container.add(right)
right_container.add(graph_frame)

state.graph_frame = graph_frame


# =========================
# UI COMPONENTS
# =========================
editor = Editor(right, state)

cho_panel = CHOPanel(left, state, None)

memory_panel = MemoryPanel(middle, editor, state)
state.memory_panel = memory_panel

metadata_panel = MetadataPanel(right, state, editor)
state.metadata_panel = metadata_panel


# =========================
# BUTTON BAR
# =========================
bar = tk.Frame(right)
bar.pack(fill="x", pady=5)

row1 = tk.Frame(bar)
row1.pack(fill="x")

tk.Button(row1, text="Compare",
    command=lambda: compare(state.current_cho)
).pack(side="left", padx=3)

tk.Button(row1, text="Search",
    command=search
).pack(side="left", padx=3)

tk.Button(row1, text="CHO RDF",
    command=lambda: export_cho_rdf(state.current_cho)
).pack(side="left", padx=3)

tk.Button(row1, text="Mem. RDF",
    command=lambda: export_memory_rdf(state.current_memory)
).pack(side="left", padx=3)


# =========================
# INIT
# =========================
cho_panel.load()
memory_panel.load()


# =========================
# APPLY EXACT PROPORTIONS ✅
# =========================
def apply_layout():
    total_w = root.winfo_width()

    # ✅ Sidebar = 25%
    sidebar_w = int(total_w * 0.25)
    main_pane.sash_place(0, sidebar_w, 0)
    
    # ✅ Right container width
    right_w = total_w - sidebar_w

    # ✅ Editor = 27.5% overall → 36.67% of right side
    editor_ratio = 0.275 / 0.75  # ≈ 0.3667
    editor_w = int(right_w * editor_ratio)

    right_container.sash_place(0, editor_w, 0)

# ✅ Apply after UI ready
root.update_idletasks()
apply_layout()


# =========================
# RUN
# =========================
root.mainloop()