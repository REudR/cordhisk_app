import re
import tkinter as tk
from tkinter import ttk

RE_METADATA = re.compile(r'<(.*?) cho="(.*?)">(.*?)</\1>')
RE_ANY_TAG = re.compile(r"<.*?>(.*?)</.*?>")
RE_STRIP = re.compile(r"</?[^>]+>")

def load_list(listbox, items, fmt):
    listbox.delete(0, tk.END)
    for item in items:
        listbox.insert(tk.END, fmt(item))

def make_tree_window(title, columns=None):
    win = tk.Toplevel()
    win.title(title)

    frame = tk.Frame(win)
    frame.pack(fill="both", expand=True)

    if columns:
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
    else:
        tree = ttk.Treeview(frame)

    scroll = ttk.Scrollbar(frame, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)

    scroll.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    return tree