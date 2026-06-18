import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os, shutil, re

import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# =========================
# CONFIG
# =========================
APP_DATA_DIR = "memory_files"
os.makedirs(APP_DATA_DIR, exist_ok=True)

# =========================
# DATABASE
# =========================
Base = declarative_base()

class CHO(Base):
    __tablename__ = "chos"
    id = Column(Integer, primary_key=True)
    custom_id = Column(String, unique=True)
    title = Column(String)

class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True)
    custom_id = Column(String, unique=True)
    title = Column(String)
    text = Column(Text)
    file_path = Column(String)

engine = create_engine("sqlite:///cordhisk.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# =========================
# GLOBAL
# =========================
current_memory = None
canvas = None
unsaved_changes = False

# =========================
# UTILS
# =========================
def extract_metadata(text):
    return [
        {"field": f, "cho": c, "value": v}
        for f, c, v in re.findall(r'<(.*?) cho="(.*?)">(.*?)</\1>', text)
    ]

def highlight_tags():
    text_box.tag_remove("tagged", "1.0", tk.END)
    for m in re.finditer(r"<.*?>(.*?)</.*?>", text_box.get("1.0", tk.END)):
        text_box.tag_add("tagged",
            f"1.0+{m.start(1)}c",
            f"1.0+{m.end(1)}c")

# =========================
# SAFE SAVE TRACKING
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
    win = tk.Toplevel()
    tree = ttk.Treeview(win)
    tree.pack(fill="both", expand=True)

    root = tree.insert("", "end", text=f"CHO {cid}")

    for m in session.query(Memory):
        mem_node = None
        for md in extract_metadata(m.text):
            if md["cho"] == cid:
                if not mem_node:
                    mem_node = tree.insert(root, "end", text=f"Memory {m.custom_id}")
                tree.insert(mem_node, "end",
                    text=f"{md['field']} → {md['value']}")

def show_memory_tree(mem):
    win = tk.Toplevel()
    tree = ttk.Treeview(win)
    tree.pack(fill="both", expand=True)

    root = tree.insert("", "end", text=f"Memory {mem.custom_id}")

    grouped = {}
    for md in extract_metadata(mem.text):
        grouped.setdefault(md["cho"], []).append(md)

    for cid, items in grouped.items():
        cho_node = tree.insert(root, "end", text=f"CHO {cid}")
        for md in items:
            tree.insert(cho_node, "end",
                text=f"{md['field']} → {md['value']}")

# =========================
# GRAPH
# =========================
def generate_graph():
    global canvas

    if canvas:
        canvas.get_tk_widget().destroy()

    fig = plt.Figure()
    ax = fig.add_subplot(111)

    G = nx.Graph()
    node_types = {}
    node_data = {}

    cho_sel = cho_list.get(tk.ACTIVE)
    mem_sel = mem_list.get(tk.ACTIVE)

    # ---- CHO GRAPH ----
    if cho_sel:
        cid = cho_sel.split(" - ")[0]

        for m in session.query(Memory):
            for md in extract_metadata(m.text):
                if md["cho"] != cid:
                    continue

                mem_node = f"M:{m.custom_id}"
                tag_node = f"T:{md['value']}"
                cho_node = f"C:{cid}"

                G.add_edge(mem_node, tag_node)
                G.add_edge(tag_node, cho_node)

                node_types[mem_node] = "memory"
                node_types[tag_node] = "tag"
                node_types[cho_node] = "cho"

                node_data[mem_node] = m
                node_data[tag_node] = md
                node_data[cho_node] = cid

    # ---- MEMORY GRAPH ----
    elif mem_sel:
        mid = mem_sel.split(" - ")[0]
        m = session.query(Memory).filter_by(custom_id=mid).first()

        for md in extract_metadata(m.text):
            mem_node = f"M:{m.custom_id}"
            cho_node = f"C:{md['cho']}"
            tag_node = f"T:{md['value']}"

            G.add_edge(mem_node, cho_node)
            G.add_edge(cho_node, tag_node)

            node_types[mem_node] = "memory"
            node_types[tag_node] = "tag"
            node_types[cho_node] = "cho"

            node_data[mem_node] = m
            node_data[tag_node] = md
            node_data[cho_node] = md["cho"]

    else:
        messagebox.showinfo("Info", "Select CHO or Memory")
        return

    pos = nx.spring_layout(G)

    nx.draw_networkx_nodes(G, pos,
        [n for n in G if node_types[n]=="cho"],
        node_shape="o", node_color="lightgreen", ax=ax)

    nx.draw_networkx_nodes(G, pos,
        [n for n in G if node_types[n]=="memory"],
        node_shape="s", node_color="lightblue", ax=ax)

    nx.draw_networkx_nodes(G, pos,
        [n for n in G if node_types[n]=="tag"],
        node_shape="h", node_color="orange", ax=ax)

    nx.draw_networkx_edges(G, pos, ax=ax)
    nx.draw_networkx_labels(G, pos, ax=ax)

    def on_click(event):
        for node, (x,y) in pos.items():
            if abs(event.xdata-x) < 0.05 and abs(event.ydata-y) < 0.05:
                if node.startswith("C:"):
                    show_cho_tree(node_data[node])
                elif node.startswith("M:"):
                    show_memory_tree(node_data[node])
                elif node.startswith("T:"):
                    md = node_data[node]
                    messagebox.showinfo("Tag",
                        f"{md['field']} → {md['value']}")
                break

    fig.canvas.mpl_connect("button_press_event", on_click)

    canvas_widget = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas_widget.draw()
    canvas_widget.get_tk_widget().pack(fill="both", expand=True)

    canvas = canvas_widget

# =========================
# COMPARE (FIXED)
# =========================
def compare():
    sel = cho_list.get(tk.ACTIVE)
    if not sel:
        messagebox.showinfo("Info", "Select a CHO")
        return

    cid = sel.split(" - ")[0]

    win = tk.Toplevel()
    tree = ttk.Treeview(win,
        columns=("Memory","Field","Value"),
        show="headings")

    for c in ("Memory","Field","Value"):
        tree.heading(c, text=c)

    tree.pack(fill="both", expand=True)

    for m in session.query(Memory):
        for md in extract_metadata(m.text):
            if md["cho"] == cid:
                tree.insert("", "end",
                    values=(m.custom_id, md["field"], md["value"]))

# =========================
# SEARCH
# =========================
def search():
    term = simpledialog.askstring("Search","Enter text")
    if not term:
        return

    win = tk.Toplevel()
    t = tk.Text(win)
    t.pack(fill="both", expand=True)

    for m in session.query(Memory):
        if term.lower() in m.text.lower():
            t.insert(tk.END, f"{m.custom_id}\n")

# =========================
# RDF EXPORT
# =========================
def export_rdf():
    sel = cho_list.get(tk.ACTIVE)
    if not sel:
        return

    cid = sel.split(" - ")[0]
    xml = "<rdf:RDF>\n"

    for m in session.query(Memory):
        meta = [x for x in extract_metadata(m.text) if x["cho"] == cid]
        if meta:
            xml += "<rdf:Description>\n"
            for x in meta:
                xml += f"<{x['field']}>{x['value']}</{x['field']}>\n"
            xml += "</rdf:Description>\n"

    xml += "</rdf:RDF>"

    path = filedialog.asksaveasfilename(defaultextension=".xml")
    if path:
        open(path,"w").write(xml)

# =========================
# UI SETUP
# =========================
root = tk.Tk()
root.title("CORDHISK App")
root.geometry("1600x800")

left = tk.Frame(root); left.pack(side="left", fill="y")
middle = tk.Frame(root); middle.pack(side="left", fill="y")
right = tk.Frame(root); right.pack(side="left", fill="both", expand=True)
graph_frame = tk.Frame(root); graph_frame.pack(side="right", fill="both", expand=True)

# =========================
# CHO PANEL
# =========================
cho_list = tk.Listbox(left)
cho_list.pack(fill="both", expand=True)

def load_chos():
    cho_list.delete(0, tk.END)
    for c in session.query(CHO):
        cho_list.insert(tk.END, f"{c.custom_id} - {c.title}")

def create_cho():
    cid = simpledialog.askstring("CHO ID","ID")
    title = simpledialog.askstring("Title","Title")
    if not cid or not title:
        return
    if session.query(CHO).filter_by(custom_id=cid).first():
        messagebox.showerror("Error","Duplicate")
        return
    session.add(CHO(custom_id=cid,title=title))
    session.commit()
    load_chos()

def delete_cho():
    sel = cho_list.get(tk.ACTIVE)
    if not sel:
        return
    cid = sel.split(" - ")[0]
    if messagebox.askyesno("Delete",cid):
        session.delete(session.query(CHO).filter_by(custom_id=cid).first())
        session.commit()
        load_chos()

tk.Button(left,text="Add CHO",command=create_cho).pack()
tk.Button(left,text="Delete CHO",command=delete_cho).pack()

# =========================
# MEMORY PANEL
# =========================
mem_list = tk.Listbox(middle)
mem_list.pack(fill="both", expand=True)

def load_memories():
    mem_list.delete(0,tk.END)
    for m in session.query(Memory):
        mem_list.insert(tk.END,f"{m.custom_id} - {m.title}")

def import_txt():
    global current_memory, unsaved_changes
    path = filedialog.askopenfilename()
    if not path:
        return
    mid = simpledialog.askstring("Memory ID","ID")
    if not mid:
        return
    if session.query(Memory).filter_by(custom_id=mid).first():
        messagebox.showerror("Error","Duplicate")
        return

    new = os.path.join(APP_DATA_DIR, f"{mid}_{os.path.basename(path)}")
    shutil.copy(path,new)

    with open(new) as f:
        txt = f.read()

    m = Memory(custom_id=mid,title="Memory",text=txt,file_path=new)
    session.add(m)
    session.commit()

    current_memory = m
    load_memories()

    text_box.delete("1.0",tk.END)
    text_box.insert(tk.END,txt)
    highlight_tags()

    unsaved_changes = False
    text_box.edit_modified(False)

def delete_memory():
    sel = mem_list.get(tk.ACTIVE)
    if not sel:
        return
    mid = sel.split(" - ")[0]
    m = session.query(Memory).filter_by(custom_id=mid).first()
    if messagebox.askyesno("Delete",mid):
        if os.path.exists(m.file_path):
            os.remove(m.file_path)
        session.delete(m)
        session.commit()
        load_memories()
        text_box.delete("1.0",tk.END)

tk.Button(middle,text="Import Memory",command=import_txt).pack()
tk.Button(middle,text="Delete Memory",command=delete_memory).pack()

# =========================
# EDITOR
# =========================
text_box = tk.Text(right)
text_box.pack(fill="both", expand=True)
text_box.tag_config("tagged",background="lightyellow")

text_box.bind("<<Modified>>", on_text_change)

def on_mem_select(event):
    global current_memory, unsaved_changes

    sel = mem_list.get(tk.ACTIVE)
    if not sel:
        return

    if unsaved_changes:
        ans = messagebox.askyesnocancel("Unsaved","Save changes?")
        if ans is None:
            return
        elif ans:
            save_memory()

    mid = sel.split(" - ")[0]
    m = session.query(Memory).filter_by(custom_id=mid).first()
    current_memory = m

    text_box.delete("1.0",tk.END)
    text_box.insert(tk.END,m.text)
    highlight_tags()

    unsaved_changes = False
    text_box.edit_modified(False)

mem_list.bind("<<ListboxSelect>>", on_mem_select)

# =========================
# EDIT FUNCTIONS
# =========================
def save_memory():
    global unsaved_changes
    if not current_memory:
        return
    txt = text_box.get("1.0",tk.END)
    current_memory.text = txt
    if current_memory.file_path:
        open(current_memory.file_path,"w").write(txt)
    session.commit()
    unsaved_changes = False
    text_box.edit_modified(False)

def add_tag():
    try:
        sel = text_box.get(tk.SEL_FIRST,tk.SEL_LAST)
        field = simpledialog.askstring("Field","dc:title etc")
        cho = simpledialog.askstring("CHO ID","Enter CHO ID")

        tagged = f'<{field} cho="{cho}">{sel}</{field}>'

        text_box.delete(tk.SEL_FIRST,tk.SEL_LAST)
        text_box.insert(tk.INSERT,tagged)
        highlight_tags()
    except:
        pass

def remove_tag():
    try:
        sel = text_box.get(tk.SEL_FIRST,tk.SEL_LAST)
        clean = re.sub(r"</?[^>]+>","",sel)
        text_box.delete(tk.SEL_FIRST,tk.SEL_LAST)
        text_box.insert(tk.INSERT,clean)
        highlight_tags()
    except:
        pass

# =========================
# BUTTON BAR
# =========================
bar = tk.Frame(right)
bar.pack()

for t,cmd in [
    ("Save",save_memory),
    ("Add Tag",add_tag),
    ("Remove Tag",remove_tag),
    ("Generate Graph",generate_graph),
    ("Compare",compare),
    ("Search",search),
    ("Export RDF",export_rdf)
]:
    tk.Button(bar,text=t,command=cmd).pack(side="left")

# =========================
# INIT
# =========================
load_chos()
load_memories()

root.mainloop()