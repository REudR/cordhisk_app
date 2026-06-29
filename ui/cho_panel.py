import tkinter as tk
from tkinter import simpledialog, messagebox
from db import session, CHO
from utils import load_list


class CHOPanel:
    def __init__(self, parent, state, label):
        self.state = state
        self.label = label
        self.chos = []

        self.listbox = tk.Listbox(parent)
        self.listbox.pack(fill="both", expand=True)

        tk.Button(parent, text="Add CHO", command=self.add).pack()
        tk.Button(parent, text="Delete CHO", command=self.delete).pack()

        self.listbox.bind("<<ListboxSelect>>", self.select)

    def load(self):
        self.chos = session.query(CHO).all()

        load_list(
            self.listbox,
            self.chos,
            lambda c: f"{c.custom_id} - {c.title}"
        )

    def add(self):
        cid = simpledialog.askstring("ID", "CHO ID")
        title = simpledialog.askstring("Title", "Title")

        if not cid or not title:
            return

        if session.query(CHO).filter_by(custom_id=cid).first():
            messagebox.showerror("Error", "Duplicate ID")
            return

        session.add(CHO(custom_id=cid, title=title))
        session.commit()
        self.load()

    def delete(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        
        sel = self.listbox.get(selection[0])

        cid = sel.split(" - ")[0]
        obj = session.query(CHO).filter_by(custom_id=cid).first()

        if obj and messagebox.askyesno("Delete", f"Delete CHO '{cid}'?"):
            session.delete(obj)
            session.commit()
            self.load()

    def select(self, event):
        self.listbox.after(1, self._select)
    
    
    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            return
    
        sel = self.listbox.get(selection[0])
    
        cid = sel.split(" - ")[0]
    
        # ✅ Set CHO selection
        self.state.current_cho = cid
        self.state.current_memory = None
    
        # ✅ Refresh metadata panel
        if hasattr(self.state, "metadata_panel"):
            self.state.metadata_panel.refresh()
    
        # ✅ Update graph
        from features.graph import generate_graph
        generate_graph(self.state.graph_frame, self.state)