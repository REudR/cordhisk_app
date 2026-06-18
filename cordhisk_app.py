import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import re
import shutil
import xml.etree.ElementTree as ET

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# =========================
# CONFIG
# =========================
APP_DATA_DIR = "memory_files"
os.makedirs(APP_DATA_DIR, exist_ok=True)
current_cho = None

# =========================
# COMPILED PATTERNS          ← compiled once at import, not on every call
# =========================
RE_METADATA = re.compile(r'<(.*?) cho="(.*?)">(.*?)</\1>')
RE_ANY_TAG  = re.compile(r"<.*?>(.*?)</.*?>")
RE_STRIP    = re.compile(r"</?[^>]+>")

# =========================
# DATABASE
# =========================
Base = declarative_base()

class CHO(Base):
    __tablename__ = "chos"
    id        = Column(Integer, primary_key=True)
    custom_id = Column(String, unique=True)
    title     = Column(String)

class Memory(Base):
    __tablename__ = "memories"
    id        = Column(Integer, primary_key=True)
    custom_id = Column(String, unique=True)
    title     = Column(String)
    text      = Column(Text)
    file_path = Column(String)

engine = create_engine("sqlite:///cordhisk.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# =========================
# GLOBAL STATE
# =========================
current_memory  = None
canvas          = None
unsaved_changes = False

# =========================
# UTILS
# =========================
def extract_metadata(text):
    """Return list of {field, cho, value} dicts found in text."""
    return [
        {"field": f, "cho": c, "value": v}
        for f, c, v in RE_METADATA.findall(text or "")
    ]

def highlight_tags():
    """Highlight tagged content in the editor."""
    text_box.tag_remove("tagged", "1.0", tk.END)
    content = text_box.get("1.0", tk.END)
    for m in RE_ANY_TAG.finditer(content):
        text_box.tag_add("tagged", f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")

def make_tree_window(title, columns=None):
    """Create a Toplevel with a scrollable Treeview; return (win, tree)."""
    win   = tk.Toplevel()
    win.title(title)
    frame = tk.Frame(win)
    frame.pack(fill="both", expand=True)
    if columns:
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
    else:
        tree = ttk.Treeview(frame)
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    return win, tree

def _load_list(listbox, model, fmt):
    """Generic listbox loader — deduplicates load_chos / load_memories."""
    listbox.delete(0, tk.END)
    for item in session.query(model):
        listbox.insert(tk.END, fmt(item))

# =========================
# CHANGE TRACKING
# =========================
def on_text_change(event):
    global unsaved_changes
    if text_box.edit_modified():
        unsaved_changes = True
        text_box.edit_modified(False)

# =========================
# TREE VIEWS
# =========================
def show_cho_tree(cid):
    _, tree     = make_tree_window(f"CHO {cid}")
    root_node   = tree.insert("", "end", text=f"CHO {cid}")
    for m in session.query(Memory):
        metadata = [md for md in extract_metadata(m.text) if md["cho"] == cid]
        if metadata:
            mem_node = tree.insert(root_node, "end", text=f"Memory {m.custom_id}")
            for md in metadata:
                tree.insert(mem_node, "end", text=f"{md['field']} → {md['value']}")

def show_memory_tree(mem):
    _, tree   = make_tree_window(f"Memory {mem.custom_id}")
    root_node = tree.insert("", "end", text=f"Memory {mem.custom_id}")
    grouped   = {}
    for md in extract_metadata(mem.text):
        grouped.setdefault(md["cho"], []).append(md)
    for cid, items in grouped.items():
        cho_node = tree.insert(root_node, "end", text=f"CHO {cid}")
        for md in items:
            tree.insert(cho_node, "end", text=f"{md['field']} → {md['value']}")

# =========================
# GRAPH
# =========================
_NODE_STYLES = {               # ← colour + shape in one place, drawn by loop
    "cho":    ("lightgreen", "o"),
    "memory": ("lightblue",  "s"),
    "tag":    ("orange",     "h"),
}

def generate_graph():
    global canvas

    cho_sel = cho_list.get(tk.ACTIVE)
    mem_sel = mem_list.get(tk.ACTIVE)

    if not cho_sel and not mem_sel:          # ← early exit before any work
        messagebox.showinfo("Info", "Select a CHO or Memory first")
        return

    if canvas:                               # ← None-safe cleanup
        canvas.get_tk_widget().destroy()
        canvas = None

    G          = nx.Graph()
    node_types = {}
    node_data  = {}

    if cho_sel:
        cid = cho_sel.split(" - ")[0]
        for m in session.query(Memory):
            for md in extract_metadata(m.text):
                if md["cho"] != cid:
                    continue
                mn, tn, cn = f"M:{m.custom_id}", f"T:{md['value']}", f"C:{cid}"
                G.add_edges_from([(mn, tn), (tn, cn)])   # ← one call instead of two
                node_types.update({mn: "memory", tn: "tag", cn: "cho"})
                node_data.update({mn: m, tn: md, cn: cid})
    else:
        mid = mem_sel.split(" - ")[0]
        m   = session.query(Memory).filter_by(custom_id=mid).first()
        if not m:
            return
        for md in extract_metadata(m.text):
            mn, cn, tn = f"M:{m.custom_id}", f"C:{md['cho']}", f"T:{md['value']}"
            G.add_edges_from([(mn, cn), (cn, tn)])
            node_types.update({mn: "memory", tn: "tag", cn: "cho"})
            node_data.update({mn: m, tn: md, cn: md["cho"]})

    fig = plt.Figure()                       # ← figure created after selection check
    ax  = fig.add_subplot(111)
    pos = nx.spring_layout(G)

    for ntype, (color, shape) in _NODE_STYLES.items():   # ← loop replaces 3 draw calls
        nodes = [n for n in G if node_types.get(n) == ntype]
        if nodes:
            nx.draw_networkx_nodes(G, pos, nodes,
                node_shape=shape, node_color=color, ax=ax)

    nx.draw_networkx_edges(G, pos, ax=ax)
    nx.draw_networkx_labels(G, pos, ax=ax)

    def on_click(event):
        if event.xdata is None or event.ydata is None:   # ← guard for out-of-axes clicks
            return
        for node, (x, y) in pos.items():
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:
                if node.startswith("C:"):
                    show_cho_tree(node_data[node])
                elif node.startswith("M:"):
                    show_memory_tree(node_data[node])
                else:
                    md = node_data[node]
                    messagebox.showinfo("Tag", f"{md['field']} → {md['value']}")
                break

    fig.canvas.mpl_connect("button_press_event", on_click)

    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

# =========================
# COMPARE
# =========================
def compare():
    sel = cho_list.get(tk.ACTIVE)
    if not sel:
        messagebox.showinfo("Info", "Select a CHO")
        return
    cid = sel.split(" - ")[0]
    _, tree = make_tree_window(f"Compare — CHO {cid}",
                               columns=("Memory", "Field", "Value"))
    for m in session.query(Memory):
        for md in extract_metadata(m.text):
            if md["cho"] == cid:
                tree.insert("", "end", values=(m.custom_id, md["field"], md["value"]))

# =========================
# SEARCH
# =========================
def search():
    term = simpledialog.askstring("Search", "Enter text")
    if not term:
        return

    # ← SQL filtering instead of loading every row into Python
    results = session.query(Memory).filter(Memory.text.ilike(f"%{term}%")).all()

    win   = tk.Toplevel()
    win.title(f'Results: "{term}"')
    frame  = tk.Frame(win)
    frame.pack(fill="both", expand=True)
    scroll = ttk.Scrollbar(frame, orient="vertical")
    t      = tk.Text(frame, yscrollcommand=scroll.set)
    scroll.configure(command=t.yview)
    scroll.pack(side="right", fill="y")
    t.pack(fill="both", expand=True)

    for m in results:
        t.insert(tk.END, f"{m.custom_id}\n")
    if not results:
        t.insert(tk.END, "No results found.")

# =========================
# RDF EXPORT
# =========================
def export_rdf():
    sel = cho_list.get(tk.ACTIVE)
    if not sel:
        return
    cid     = sel.split(" - ")[0]
    root_el = ET.Element("rdf:RDF")          # ← ElementTree instead of string concat
    for m in session.query(Memory):
        meta = [x for x in extract_metadata(m.text) if x["cho"] == cid]
        if meta:
            desc = ET.SubElement(root_el, "rdf:Description")
            for x in meta:
                ET.SubElement(desc, x["field"]).text = x["value"]
    path = filedialog.asksaveasfilename(defaultextension=".xml")
    if path:
        with open(path, "w", encoding="utf-8") as f:   # ← context manager
            f.write(ET.tostring(root_el, encoding="unicode"))

# =========================
# UI SETUP
# =========================
root = tk.Tk()
root.title("CORDHISK App")
root.geometry("1600x800")

left        = tk.Frame(root); left.pack(side="left", fill="y")
middle      = tk.Frame(root); middle.pack(side="left", fill="y")
right       = tk.Frame(root); right.pack(side="left", fill="both", expand=True)
graph_frame = tk.Frame(root); graph_frame.pack(side="right", fill="both", expand=True)

# =========================
# CHO PANEL
# =========================
cho_list = tk.Listbox(left)
cho_list.pack(fill="both", expand=True)

def load_chos():
    _load_list(cho_list, CHO, lambda c: f"{c.custom_id} - {c.title}")

def create_cho():
    cid   = simpledialog.askstring("CHO ID", "ID")
    title = simpledialog.askstring("Title", "Title")
    if not cid or not title:
        return
    if session.query(CHO).filter_by(custom_id=cid).first():
        messagebox.showerror("Error", "Duplicate CHO ID")
        return
    session.add(CHO(custom_id=cid, title=title))
    session.commit()
    load_chos()

def delete_cho():
    sel = cho_list.get(tk.ACTIVE)
    if not sel:
        return
    cid = sel.split(" - ")[0]
    obj = session.query(CHO).filter_by(custom_id=cid).first()
    if obj and messagebox.askyesno("Delete", f"Delete CHO '{cid}'?"):
        session.delete(obj)
        session.commit()
        load_chos()

tk.Button(left, text="Add CHO",    command=create_cho).pack()
tk.Button(left, text="Delete CHO", command=delete_cho).pack()

# =========================
# MEMORY PANEL
# =========================
mem_list = tk.Listbox(middle)
mem_list.pack(fill="both", expand=True)

def load_memories():
    _load_list(mem_list, Memory, lambda m: f"{m.custom_id} - {m.title}")

def import_txt():
    global current_memory, unsaved_changes
    path = filedialog.askopenfilename()
    if not path:
        return
    mid = simpledialog.askstring("Memory ID", "ID")
    if not mid:
        return
    title = simpledialog.askstring("Title", "Memory title") or "Memory"  # ← was hardcoded
    if session.query(Memory).filter_by(custom_id=mid).first():
        messagebox.showerror("Error", "Duplicate Memory ID")
        return
    new_path = os.path.join(APP_DATA_DIR, f"{mid}_{os.path.basename(path)}")
    shutil.copy(path, new_path)
    with open(new_path, encoding="utf-8", errors="replace") as f:  # ← context manager + encoding
        txt = f.read()
    m = Memory(custom_id=mid, title=title, text=txt, file_path=new_path)
    session.add(m)
    session.commit()
    current_memory = m
    load_memories()
    text_box.delete("1.0", tk.END)
    text_box.insert(tk.END, txt)
    highlight_tags()
    unsaved_changes = False
    text_box.edit_modified(False)

def delete_memory():
    sel = mem_list.get(tk.ACTIVE)
    if not sel:
        return
    mid = sel.split(" - ")[0]
    m   = session.query(Memory).filter_by(custom_id=mid).first()
    if m and messagebox.askyesno("Delete", f"Delete Memory '{mid}'?"):
        if m.file_path and os.path.exists(m.file_path):  # ← None-safe file check
            os.remove(m.file_path)
        session.delete(m)
        session.commit()
        load_memories()
        text_box.delete("1.0", tk.END)

tk.Button(middle, text="Import Memory", command=import_txt).pack()
tk.Button(middle, text="Delete Memory", command=delete_memory).pack()

# =========================
# EDITOR
# =========================
text_box = tk.Text(right)
text_box.pack(fill="both", expand=True)
text_box.tag_config("tagged", background="lightyellow")
text_box.bind("<<Modified>>", on_text_change)

def on_mem_select(event):
    global current_memory, unsaved_changes
    sel = mem_list.get(tk.ACTIVE)
    if not sel:
        return
    if unsaved_changes:
        ans = messagebox.askyesnocancel("Unsaved", "Save changes?")
        if ans is None:
            return
        if ans:
            save_memory()
    mid = sel.split(" - ")[0]
    m   = session.query(Memory).filter_by(custom_id=mid).first()
    if not m:                                # ← guard against stale selection
        return
    current_memory = m
    text_box.delete("1.0", tk.END)
    text_box.insert(tk.END, m.text or "")
    highlight_tags()
    unsaved_changes = False
    text_box.edit_modified(False)

mem_list.bind("<<ListboxSelect>>", on_mem_select)

# =========================
# EDITOR ACTIONS
# =========================
def save_memory():
    global unsaved_changes
    if not current_memory:
        return
    txt = text_box.get("1.0", tk.END)
    current_memory.text = txt
    if current_memory.file_path:
        with open(current_memory.file_path, "w", encoding="utf-8") as f:  # ← context manager
            f.write(txt)
    session.commit()
    unsaved_changes = False
    text_box.edit_modified(False)



def add_tag():
    try:
        sel = text_box.get(tk.SEL_FIRST, tk.SEL_LAST)

        if not current_cho:
            messagebox.showerror("Error", "Select a CHO first")
            return
        cho = current_cho

        field = field_selector.get()
        if not field:
            messagebox.showerror("Error", "Select a metadata field")
            return

        tagged = f'<{field} cho="{cho}">{sel}</{field}>'

        text_box.delete(tk.SEL_FIRST, tk.SEL_LAST)
        text_box.insert(tk.INSERT, tagged)

        highlight_tags()

    except tk.TclError:
        messagebox.showerror("Error", "Select some text first")



def remove_tag():
    try:
        sel   = text_box.get(tk.SEL_FIRST, tk.SEL_LAST)
        clean = RE_STRIP.sub("", sel)        # ← compiled pattern
        text_box.delete(tk.SEL_FIRST, tk.SEL_LAST)
        text_box.insert(tk.INSERT, clean)
        highlight_tags()
    except tk.TclError:
        pass


def on_cho_select(event):
    global current_cho
    sel = cho_list.curselection()
    if not sel:
        current_cho = None
        cho_label.config(text="No CHO selected")
        return

    value = cho_list.get(sel[0])
    current_cho = value.split(" - ")[0]
    cho_label.config(text=f"Active CHO: {current_cho}")

cho_list.bind("<<ListboxSelect>>", on_cho_select)

# =========================
# BUTTON BAR
# =========================
bar = tk.Frame(right)
bar.pack()

cho_label = tk.Label(bar, text="No CHO selected", fg="blue")
cho_label.pack(side="left", padx=10)

metadata_fields = [
    "dc:title",
    "dc:creator",
    "dc:date",
    "dc:subject",
    "dc:description"
]

field_selector = ttk.Combobox(bar, values=metadata_fields, width=20)
field_selector.set("dc:title")
field_selector.pack(side="left", padx=5)



for label, cmd in [
    ("Save",           save_memory),
    ("Add Tag",        add_tag),
    ("Remove Tag",     remove_tag),
    ("Generate Graph", generate_graph),
    ("Compare",        compare),
    ("Search",         search),
    ("Export RDF",     export_rdf),
]:
    tk.Button(bar, text=label, command=cmd).pack(side="left")


# =========================
# INIT
# =========================
load_chos()
load_memories()

root.mainloop()
