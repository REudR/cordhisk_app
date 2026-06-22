import tkinter as tk
from tkinter import simpledialog, messagebox
from db import session, CHO
from utils import load_list

class CHOPanel:
    def __init__(self, parent, state, label):
        self.state = state
        self.label = label

        self.listbox = tk.Listbox(parent)
        self.listbox.pack(fill="both", expand=True)

        tk.Button(parent, text="Add CHO", command=self.add).pack()
        tk.Button(parent, text="Delete CHO", command=self.delete).pack()

        self.listbox.bind("<<ListboxSelect>>", self.select)

    def load(self):
        load_list(self.listbox, session.query(CHO),
                  lambda c: f"{c.custom_id} - {c.title}")

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
        sel = self.listbox.get(tk.ACTIVE)
        if not sel:
            return

        cid = sel.split(" - ")[0]
        obj = session.query(CHO).filter_by(custom_id=cid).first()

        if obj and messagebox.askyesno("Delete", f"Delete CHO '{cid}'?"):
            session.delete(obj)
            session.commit()
            self.load()

    def select(self, e):
        sel = self.listbox.curselection()
        if not sel:
            self.state.current_cho = None
            self.label.config(text="No CHO selected")
            return

        value = self.listbox.get(sel[0])
        cid = value.split(" - ")[0]

        self.state.current_cho = cid
        self.label.config(text=f"Active CHO: {cid}")
                    
        if self.label:
            self.label.config(text=f"Active CHO: {cid}")
