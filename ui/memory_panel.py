import tkinter as tk
from tkinter import filedialog, messagebox
import re
import html

from db import session, Memory
from utils import load_list
from services.types import MetadataType
from services.file_service import copy_memory_file
from services.metadata import extract_metadata, parse_text_and_spans
from services.memory_service import rebuild_memory_text  # ✅ NEW
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

    # =========================
    # EDIT MEMORY METADATA ✅ SIMPLIFIED
    # =========================
    def edit_memory_metadata(self, event=None):
        m = self.state.current_memory
        if not m:
            messagebox.showwarning("No selection", "Select a memory first.")
            return

        # read current file
        try:
            with open(m.file_path, encoding="utf-8", errors="replace") as f:
                txt = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read file:\n{e}")
            return

        txt = html.unescape(txt)

        # extract existing metadata
        existing_memory_md = self.extract_memory_block_metadata(txt)

        # open form
        form = ask_memory_full_form(
            initial_metadata=existing_memory_md,
            initial_id=m.custom_id,
            parent=self.state.root
        )

        if not form:
            return

        new_metadata = form["metadata"]

        # ✅ CENTRALIZED REBUILD
        final_text = rebuild_memory_text(txt, new_metadata)

        # update DB + file
        try:
            with open(m.file_path, "w", encoding="utf-8") as f:
                f.write(final_text)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot write file:\n{e}")
            return

        m.text = final_text
        m.title = new_metadata.get("dc:title", m.custom_id)

        session.commit()

        # refresh UI
        self.editor.load(m)

        if hasattr(self.state, "metadata_panel"):
            self.state.metadata_panel.refresh()

        from features.graph import generate_graph
        generate_graph(self.state.graph_frame, self.state)

        messagebox.showinfo("Success", "Memory metadata updated.")

    # =========================
    # LOAD
    # =========================
    def load(self):
        load_list(
            self.listbox,
            session.query(Memory),
            lambda m: f"{m.custom_id} - {m.title}"
        )

    # =========================
    # SELECT MEMORY
    # =========================
    def select(self, event):
        # ✅ delay execution so selection is updated
        self.listbox.after(1, self._select)
    
    
    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            return
    
        sel = self.listbox.get(selection[0])
    
        mid = sel.split(" - ")[0]
        m = session.query(Memory).filter_by(custom_id=mid).first()
    
        if m:
            self.state.current_memory = m
            self.state.current_cho = None
    
            self.editor.load(m)
    
            if hasattr(self.state, "metadata_panel"):
                self.state.metadata_panel.refresh()
    
            from features.graph import generate_graph
            generate_graph(self.state.graph_frame, self.state)

    # =========================
    # EXTRACT MEMORY BLOCK
    # =========================
    def extract_memory_block_metadata(self, text):
        from services.metadata import COMBINED_RE

        block_pattern = r'===\s*MEMORY METADATA START\s*===(.*?)===\s*MEMORY METADATA END\s*==='
        match = re.search(block_pattern, text or "", re.DOTALL)

        metadata = {}

        if match:
            block = match.group(1)

            for m in COMBINED_RE.finditer(block):
                if m.group("type") == "memory":
                    metadata[m.group("field")] = m.group("value")

        return metadata

    # =========================
    # IMPORT FILE ✅ CLEANED
    # =========================
    def import_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return

        new_path = copy_memory_file(path, "temp")

        with open(new_path, encoding="utf-8", errors="replace") as f:
            txt = f.read()

        txt = html.unescape(txt)
        txt = re.sub(r'<rdf:RDF.*?</rdf:RDF>', '', txt, flags=re.DOTALL)

        existing_memory_md = self.extract_memory_block_metadata(txt)

        use_existing = False
        if existing_memory_md:
            use_existing = messagebox.askyesno(
                "Memory metadata detected",
                f"Detected {len(existing_memory_md)} fields.\n\nUse them?"
            )

        form = ask_memory_full_form(
            existing_memory_md if use_existing else {},
            initial_id=None,
            parent=self.state.root
        )

        if not form:
            return

        mid = form["id"]
        metadata = form["metadata"]

        new_path = copy_memory_file(path, mid)

        # ✅ CENTRALIZED REBUILD
        final_text = rebuild_memory_text(txt, metadata)

        m = Memory(
            custom_id=mid,
            title=metadata.get("dc:title", mid),
            text=final_text,
            file_path=new_path
        )

        session.add(m)
        session.commit()

        self.load()
        self.state.current_memory = m
        self.state.current_cho = None

        self.editor.load(m)

        if hasattr(self.state, "metadata_panel"):
            self.state.metadata_panel.refresh()

        from features.graph import generate_graph
        generate_graph(self.state.graph_frame, self.state)

    # =========================
    # DELETE
    # =========================
    def delete(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        
        sel = self.listbox.get(selection[0])

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