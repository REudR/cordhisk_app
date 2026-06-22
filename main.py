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
left = tk.Frame(root)
left.pack(side="left", fill="y")

middle = tk.Frame(root)
middle.pack(side="left", fill="y")

right = tk.Frame(root)
right.pack(side="left", fill="both", expand=True)

graph_frame = tk.Frame(root)
graph_frame.pack(side="right", fill="both", expand=True)

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

cho_selector = ttk.Combobox(row1, width=15)
cho_selector.pack(side="left", padx=5)

def refresh_cho_selector():
    from db import session, CHO

    chos = [c.custom_id for c in session.query(CHO)]
    cho_selector["values"] = chos

    if chos:
        cho_selector.set(chos[0])
        state.current_cho = chos[0]

def on_cho_change(event):
    state.current_cho = cho_selector.get()
    generate_graph(graph_frame, state)

cho_selector.bind("<<ComboboxSelected>>", on_cho_change)

refresh_cho_selector()
state.current_cho = cho_selector.get()

field_selector = ttk.Combobox(
    row1,
    values=["dc:title", "dc:creator", "dc:date", "dc:subject", "dc:description"],
    width=15
)
field_selector.set("dc:title")
field_selector.pack(side="left", padx=5)

def on_field_change(event):
    state.current_field = field_selector.get()

field_selector.bind("<<ComboboxSelected>>", on_field_change)

state.current_field = field_selector.get()

tk.Button(row1, text="Save", command=editor.save).pack(side="left", padx=3)

tk.Button(
    row1,
    text="Add Tag",

        command=lambda: editor.add_tag(
            state.current_field,
            cho_selector.get()
        )

).pack(side="left", padx=3)

tk.Button(
    row1,
    text="Remove Tag",
    command=metadata_panel.delete
).pack(side="left", padx=3)

# ---- Row 2 (analysis tools) ----
row2 = tk.Frame(bar)
row2.pack(fill="x")

tk.Button(
    row2,
    text="Generate Graph",
    command=lambda: generate_graph(graph_frame, state)
).pack(side="left", padx=3)

tk.Button(
    row2,
    text="Compare",
    command=lambda: compare(state.current_cho)
).pack(side="left", padx=3)

tk.Button(row2, text="Search", command=search).pack(side="left", padx=3)

tk.Button(
    row2,
    text="CHO RDF",
    command=lambda: export_cho_rdf(state.current_cho)
).pack(side="left", padx=3)

tk.Button(
    row2,
    text="Mem. RDF",
    command=lambda: export_memory_rdf(state.current_memory)
).pack(side="left", padx=3)

# =========================
# INIT
# =========================

cho_panel.load()
refresh_cho_selector()

memory_panel.load()

root.mainloop()