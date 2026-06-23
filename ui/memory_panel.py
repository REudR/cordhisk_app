import tkinter as tk
from tkinter import filedialog, messagebox
from db import session, Memory
from utils import load_list, MetadataType
from services.file_service import copy_memory_file
from services.metadata import build_rdf_block
from ui.dialogs import ask_memory_full_form

class MemoryPanel:
    def __init__(self, parent, editor, state):
        self.editor = editor
        self.state = state

        self.listbox = tk.Listbox(parent)
        self.listbox.pack(fill="both", expand=True)

        tk.Button(parent, text="Import Memory", command=self.import_file).pack()
        tk.Button(parent, text="Delete Memory", command=self.delete).pack()

        self.listbox.bind("<<ListboxSelect>>", self.select)

    def load(self):
        load_list(self.listbox, session.query(Memory),
            lambda m: f"{m.custom_id} - {m.title}")

    def select(self, e):
        sel = self.listbox.get(tk.ACTIVE)
        if not sel:
            return
    
        mid = sel.split(" - ")[0]
        m = session.query(Memory).filter_by(custom_id=mid).first()
    
        if m:
            self.state.current_memory = m   # ✅ CRITICAL FIX
            self.state.current_cho = None  # Reset CHO when selecting memory
            self.editor.load(m)
            
            from features.graph import generate_graph
            generate_graph(self.state.graph_frame, self.state)

    def import_file(self):
        
        path = filedialog.askopenfilename()
        if not path:
            return

        form = ask_memory_full_form()
        if not form:
            return

        mid = form["id"]
        metadata = form["metadata"]

        new_path = copy_memory_file(path, mid)

        with open(new_path, encoding="utf-8", errors="replace") as f:
            txt = f.read()

        rdf_block = build_rdf_block(metadata)
        
        # ✅ FIX: Wrap metadata with type="memory" to mark as memory-intrinsic, not CHO-linked
        inline_metadata = ""
        for field, value in metadata.items():
            inline_metadata += f'<{field} type="memory">{value}</{field}>\n'
        
        txt = rdf_block + inline_metadata + "\n" + txt

        m = Memory(
            custom_id=mid,
            title=metadata.get("dc:title", mid),
            text=txt,
            file_path=new_path
        )

        session.add(m)
        session.commit()

        self.load()
        self.state.current_memory = m
        self.state.current_cho = None  # Reset CHO
        self.editor.load(m)
        from features.graph import generate_graph
        generate_graph(self.editor.text.master.master.graph_frame, self.state)

    def delete(self):
        sel = self.listbox.get(tk.ACTIVE)
        if not sel:
            return

        mid = sel.split(" - ")[0]
        m = session.query(Memory).filter_by(custom_id=mid).first()

        if m and messagebox.askyesno("Delete", f"Delete {mid}?"):
            if m.file_path:
                import os
                if os.path.exists(m.file_path):
                    os.remove(m.file_path)

            session.delete(m)
            session.commit()
            self.load()
