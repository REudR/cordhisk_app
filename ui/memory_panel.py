import tkinter as tk
from tkinter import filedialog, messagebox
import re
import html
from services.metadata import parse_text_and_spans
from db import session, Memory
from utils import load_list, MetadataType
from services.file_service import copy_memory_file
from services.metadata import (
    extract_metadata,
    parse_text_and_spans,
    rebuild_text_from_spans,
    COMBINED_RE
)
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

    def edit_memory_metadata(self, event=None):
        m = self.state.current_memory
        if not m:
            messagebox.showwarning("No selection", "Select a memory first.")
            return
    
        # =========================
        # STEP 1 — LOAD FILE TEXT
        # =========================
        try:
            with open(m.file_path, encoding="utf-8", errors="replace") as f:
                txt = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read file:\n{e}")
            return
    
        txt = html.unescape(txt)
        txt = txt.replace("\r\n", "\n").strip()
    
        # =========================
        # STEP 2 — EXTRACT EXISTING MEMORY METADATA
        # =========================
        existing_memory_md = self.extract_memory_block_metadata(txt)
    
        # =========================
        # STEP 3 — OPEN FORM (PREFILLED ✅)
        # =========================
        form = ask_memory_full_form(
            initial_metadata=existing_memory_md,
            initial_id=m.custom_id
        )
        
        if not form:
            return
        
        # ⚠️ IMPORTANT: DO NOT allow ID changes silently
        mid = m.custom_id
        new_metadata = form["metadata"]
    
        # =========================
        # STEP 4 — REMOVE OLD MEMORY BLOCK
        # =========================
        txt_no_block = re.sub(
            r'===\s*MEMORY METADATA START\s*===.*?===\s*MEMORY METADATA END\s*===',
            '',
            txt,
            flags=re.DOTALL
        )
    
        # =========================
        # STEP 5 — PARSE TEXT
        # =========================
        clean, _ = parse_text_and_spans(txt_no_block)
    
        # =========================
        # STEP 6 — PRESERVE CHO METADATA
        # =========================
        existing_cho_md = [
            md for md in extract_metadata(txt)
            if md.get("type") == MetadataType.CHO.value
        ]
    
        spans = []
    
        # keep CHO
        for md in existing_cho_md:
            start = clean.find(md["value"])
            if start == -1:
                continue
    
            spans.append({
                "start": start,
                "end": start + len(md["value"]),
                "field": md["field"],
                "value": md["value"],
                "cho": md.get("cho"),
                "type": MetadataType.CHO.value
            })
    
        # add MEMORY metadata
        for field, value in new_metadata.items():
            start = clean.find(value)
    
            if start == -1:
                # still keep metadata even if not found in text
                spans.append({
                    "field": field,
                    "value": value,
                    "type": MetadataType.MEMORY.value
                })
                continue
    
            spans.append({
                "start": start,
                "end": start + len(value),
                "field": field,
                "value": value,
                "type": MetadataType.MEMORY.value
            })
    
        # =========================
        # STEP 7 — BUILD NEW MEMORY BLOCK (FIXED)
        # =========================
        lines = [
            f'<{field} type="memory">{value}</{field}>'
            for field, value in new_metadata.items()
            if value.strip()
        ]
        
        meta_block = (
            "=== MEMORY METADATA START ===\n"
            + "\n".join(lines)
            + "\n=== MEMORY METADATA END ===\n\n"
        )
    
        # =========================
        # STEP 8 — REBUILD TEXT
        # =========================
        content_text = rebuild_text_from_spans(clean, spans).lstrip("\n")
        final_text = meta_block + content_text
    
        # =========================
        # STEP 9 — SAVE FILE
        # =========================
        try:
            with open(m.file_path, "w", encoding="utf-8") as f:
                f.write(final_text)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot write file:\n{e}")
            return
    
        # =========================
        # STEP 10 — UPDATE DB
        # =========================
        m.text = final_text
        m.title = new_metadata.get("dc:title", m.custom_id)
    
        session.commit()
    
        # =========================
        # STEP 11 — REFRESH UI
        # =========================
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
    def select(self, e):
        sel = self.listbox.get(tk.ACTIVE)
        if not sel:
            return
    
        mid = sel.split(" - ")[0]
        m = session.query(Memory).filter_by(custom_id=mid).first()
    
        if m:
            # ✅ set state FIRST
            self.state.current_memory = m
            self.state.current_cho = None
    
            # ✅ THEN load editor
            self.editor.load(m)
    
            # ✅ THEN update metadata panel
            if hasattr(self.state, "metadata_panel"):
                self.state.metadata_panel.refresh()
    
            # ✅ THEN generate graph (after everything is ready)
            from features.graph import generate_graph
            generate_graph(self.state.graph_frame, self.state)

    # =========================
    # EXTRACT MEMORY BLOCK
    # =========================
    def extract_memory_block_metadata(self, text):
        block_pattern = r'===\s*MEMORY METADATA START\s*===(.*?)===\s*MEMORY METADATA END\s*==='
        match = re.search(block_pattern, text or "", re.DOTALL)

        metadata = {}

        if match:
            block = match.group(1)

            for m in COMBINED_RE.finditer(block):
                if m.group("type") == "memory":
                    metadata[m.group("field")] = m.group("value")

        return metadata

    # ✅ NEW: combine metadata sources
    def get_all_metadata(self, text):
        memory_md = self.extract_memory_block_metadata(text)

        cho_md = extract_metadata(text)

        metadata = []

        # memory metadata
        for k, v in memory_md.items():
            metadata.append({
                "field": k,
                "value": v,
                "type": MetadataType.MEMORY.value
            })

        # CHO metadata
        metadata.extend(cho_md)

        return metadata

    def import_file(self):
    
        path = filedialog.askopenfilename()
        if not path:
            return
    
        new_path = copy_memory_file(path, "temp")  # temp id
    
        with open(new_path, encoding="utf-8", errors="replace") as f:
            txt = f.read()
    
        txt = html.unescape(txt)
        txt = txt.replace("\r\n", "\n").strip()
    
        # remove RDF
        txt = re.sub(r'<rdf:RDF.*?</rdf:RDF>', '', txt, flags=re.DOTALL)
    
        # =========================
        # STEP 1 — DETECT MEMORY METADATA
        # =========================
        existing_memory_md = self.extract_memory_block_metadata(txt)
    
        if existing_memory_md:
            use_existing = messagebox.askyesno(
                "Memory metadata detected",
                f"Detected {len(existing_memory_md)} fields.\n\nUse them?"
            )
        else:
            use_existing = False
    
        # =========================
        # STEP 2 — OPEN FORM ✅
        # =========================
        initial_metadata = existing_memory_md if use_existing else {}
    
        form = ask_memory_full_form(
            initial_metadata,
            initial_id=None,              # ✅ important: this is a NEW memory
            parent=self.state.root
        )
    
        if not form:
            return
    
        mid = form["id"]
        metadata = form["metadata"]
    
        # rename file correctly now
        new_path = copy_memory_file(path, mid)
    
        # =========================
        # STEP 3 — REMOVE MEMORY BLOCK
        # =========================
        txt = re.sub(
            r'===\s*MEMORY METADATA START\s*===.*?===\s*MEMORY METADATA END\s*===',
            '',
            txt,
            flags=re.DOTALL
        )
    
        # =========================
        # STEP 4 — PARSE TEXT
        # =========================
        clean, _ = parse_text_and_spans(txt)
    
        # =========================
        # STEP 5 — DETECT CHO METADATA
        # =========================
        existing_cho_md = [
            md for md in extract_metadata(txt)
            if md.get("type") == MetadataType.CHO.value
        ]
    
        if existing_cho_md:
            keep_cho = messagebox.askyesno(
                "CHO metadata detected",
                f"Detected {len(existing_cho_md)} CHO tags.\n\nKeep them?"
            )
        else:
            keep_cho = False
    
        # =========================
        # STEP 6 — BUILD SPANS
        # =========================
        spans = []
    
        if keep_cho:
            for md in existing_cho_md:
                start = clean.find(md["value"])
                if start == -1:
                    continue
    
                spans.append({
                    "start": start,
                    "end": start + len(md["value"]),
                    "field": md["field"],
                    "value": md["value"],
                    "cho": md.get("cho"),
                    "type": MetadataType.CHO.value
                })
    
        for field, value in metadata.items():
            start = clean.find(value)
            if start == -1:
                continue
    
            spans.append({
                "start": start,
                "end": start + len(value),
                "field": field,
                "value": value,
                "type": MetadataType.MEMORY.value
            })
    
        # =========================
        # STEP 7 — BUILD MEMORY BLOCK ✅ FIXED
        # =========================
        lines = [
            f'<{field} type="memory">{value}</{field}>'
            for field, value in metadata.items()
            if value.strip()
        ]
    
        meta_block = (
            "=== MEMORY METADATA START ===\n"
            + "\n".join(lines)
            + "\n=== MEMORY METADATA END ===\n\n"
        )
    
        # =========================
        # STEP 8 — FINAL TEXT ✅ FIXED
        # =========================
        content_text = rebuild_text_from_spans(clean, spans).lstrip("\n")
        final_text = meta_block + content_text
    
        # =========================
        # SAVE
        # =========================
        m = Memory(
            custom_id=mid,
            title=metadata.get("dc:title", mid),
            text=final_text,
            file_path=new_path
        )
    
        session.add(m)
        session.commit()
    
        # =========================
        # LOAD
        # =========================
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