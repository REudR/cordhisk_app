import tkinter as tk
import re
from tkinter import messagebox

from db import session
from services.metadata import parse_text_and_spans, rebuild_text_from_spans
from utils import MetadataType


class Editor:
    def __init__(self, parent, state):
        self.state = state
        self.loading = False

        self.text = tk.Text(parent)
        self.text.pack(fill="both", expand=True)

        # ✅ Two highlight styles
        self.text.tag_config("memory_meta", background="#a1d99b")  # green
        self.text.tag_config("cho_meta", background="#cce5ff")     # light blue

        self.text.bind("<<Modified>>", self.on_change)

    # =========================
    # TEXT CHANGE HANDLER
    # =========================
    def on_change(self, event):
        if self.loading:
            return

        if self.text.edit_modified():
            self.text.edit_modified(False)

    # =========================
    # LOAD MEMORY
    # =========================
    def load(self, memory):
        self.state.current_memory = memory
        self.loading = True

        text = memory.text or ""

        # ✅ Remove RDF block completely
        text = re.sub(r'<rdf:RDF.*?</rdf:RDF>', '', text, flags=re.DOTALL)

        # ✅ Parse clean text + spans
        clean, spans = parse_text_and_spans(text)
        self.state.spans = spans

        # ✅ Show only clean text (no tags)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", clean)

        self.loading = False

        # ✅ Apply highlights
        self.highlight_spans()

        if hasattr(self.state, "metadata_panel"):
            self.state.metadata_panel.refresh()

    # =========================
    # SAVE MEMORY
    # =========================
    def save(self):
        m = self.state.current_memory
        if not m:
            return
    
        txt = self.text.get("1.0", tk.END)
        spans = list(self.state.spans)
    
        # =========================
        # STEP 1: rebuild inline tags
        # =========================
        content = rebuild_text_from_spans(txt, spans)
    
        # =========================
        # STEP 2: rebuild memory metadata block
        # =========================
        metadata = []
        seen = set()
    
        for s in spans:
            if s.get("type") == MetadataType.MEMORY.value:
                field = s.get("field")
                value = s.get("value")
    
                if not field or not value:
                    continue
    
                key = (field, value)
                if key in seen:
                    continue
                seen.add(key)
    
                metadata.append((field, value))
    
        block = "=== MEMORY METADATA START ===\n"
    
        for field, value in metadata:
            block += f'<{field} type="memory">{value}</{field}>\n'
    
        block += "=== MEMORY METADATA END ===\n"
    
        # ✅ Clean join (no extra blank lines)
        final = block + content.lstrip("\n")
    
        # =========================
        # STEP 3: update model
        # =========================
        m.text = final
    
        # ✅ Update title field (critical for left panel)
        for field, value in metadata:
            if field == "dc:title":
                m.title = value
                break
    
        # =========================
        # STEP 4: write file
        # =========================
        if m.file_path:
            with open(m.file_path, "w", encoding="utf-8") as f:
                f.write(final)
    
        # =========================
        # STEP 5: commit DB
        # =========================
        session.commit()
    
        # =========================
        # STEP 6: refresh UI (left panel) ✅
        # =========================
        if hasattr(self.state, "memory_panel"):
            self.state.memory_panel.load()
    # =========================
    # HIGHLIGHT METADATA
    # =========================
    def highlight_spans(self):
        # Remove previous highlights
        self.text.tag_remove("memory_meta", "1.0", tk.END)
        self.text.tag_remove("cho_meta", "1.0", tk.END)

        for s in getattr(self.state, "spans", []):
        
            # ✅ SKIP spans without positions
            if "start" not in s or "end" not in s:
                continue
        
            try:
                if s.get("type") == MetadataType.MEMORY.value:
                    tag = "memory_meta"
                elif s.get("type") == MetadataType.CHO.value:
                    tag = "cho_meta"
                else:
                    continue
        
                self.text.tag_add(
                    tag,
                    f"1.0+{s['start']}c",
                    f"1.0+{s['end']}c"
                )
        
            except Exception as e:
                print("Highlight error:", e)

    # =========================
    # ADD TAG
    # =========================
    def add_tag(self, field, cho):
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)

            start = int(self.text.count("1.0", sel_start)[0])
            end = int(self.text.count("1.0", sel_end)[0])

            value = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)

        except tk.TclError:
            messagebox.showerror("Error", "Select text first")
            return

        if not field:
            messagebox.showerror("Error", "Missing field")
            return

        # ✅ Default: memory metadata
        span = {
            "start": start,
            "end": end,
            "field": field,
            "value": value,
            "type": MetadataType.MEMORY.value
        }

        # ✅ If CHO provided → override type
        if cho:
            span["cho"] = cho
            span["type"] = MetadataType.CHO.value

        # Avoid duplicates
        for s in self.state.spans:
            if s["start"] == start and s["end"] == end:
                return

        self.state.spans.append(span)
        self.state.spans.sort(key=lambda s: s["start"])

        self.highlight_spans()

        if hasattr(self.state, "metadata_panel"):
            self.state.metadata_panel.refresh()

    # =========================
    # REMOVE TAG
    # =========================
    def remove_tag(self):
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)

            start = int(self.text.count("1.0", sel_start)[0])
            end = int(self.text.count("1.0", sel_end)[0])

            # Remove matching span
            self.state.spans = [
                s for s in self.state.spans
                if not (s["start"] == start and s["end"] == end)
            ]

            self.highlight_spans()

        except tk.TclError:
            pass
