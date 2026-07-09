import tkinter as tk
import re
import html
from tkinter import messagebox
import tkinter.font as tkFont

from db import session
from services.metadata import parse_text_and_spans
from services.memory_service import rebuild_from_spans
from services.types import MetadataType


class Editor:
    def __init__(self, parent, state):
        self.state = state
        self.loading = False

        self.font = tkFont.Font(family="Helvetica", size=12)

        self.text = tk.Text(
            parent,
            wrap=tk.WORD,    
            font=self.font,
            padx=10,
            pady=10,
            undo=True
        )
        self.text.pack(fill="both", expand=True)

        self.text.tag_config("memory_meta", background="#a1d99b")
        self.text.tag_config("cho_meta", background="#cce5ff")

        self.text.bind("<<Modified>>", self.on_change)

    # =========================
    # TEXT NORMALIZATION
    # =========================
    def prepare_text(self, text):
        if not text:
            return ""

        # decode HTML
        text = html.unescape(text)

        # fix non-breaking spaces
        text = text.replace("\u00A0", " ")

        # remove RDF blocks safely
        text = re.sub(r'<rdf:RDF.*?</rdf:RDF>', '', text, flags=re.DOTALL)

        # fix broken line breaks inside words
        text = re.sub(r'(\w)\n(\w)', r'\1 \2', text)

        # normalize spaces
        text = re.sub(r' +', ' ', text)

        return text

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

        text = self.prepare_text(text)

        clean, spans = parse_text_and_spans(text)
        self.state.spans = spans

        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", clean)

        self.loading = False

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

        final, metadata = rebuild_from_spans(txt, spans)

        m.text = final

        if "dc:title" in metadata:
            m.title = metadata["dc:title"]

        if m.file_path:
            with open(m.file_path, "w", encoding="utf-8") as f:
                f.write(final)

        session.commit()

        if hasattr(self.state, "memory_panel"):
            self.state.memory_panel.load()

    # =========================
    # HIGHLIGHT SPANS
    # =========================
    def highlight_spans(self):
        self.text.tag_remove("memory_meta", "1.0", tk.END)
        self.text.tag_remove("cho_meta", "1.0", tk.END)

        for s in getattr(self.state, "spans", []):
            if "start" not in s or "end" not in s:
                continue

            try:
                tag = (
                    "memory_meta"
                    if s.get("type") == MetadataType.MEMORY.value
                    else "cho_meta"
                )

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

        span = {
            "start": start,
            "end": end,
            "field": field,
            "value": value,
            "type": MetadataType.MEMORY.value
        }

        if cho:
            span["cho"] = cho
            span["type"] = MetadataType.CHO.value

        if any(s["start"] == start and s["end"] == end for s in self.state.spans):
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

            self.state.spans = [
                s for s in self.state.spans
                if not (s["start"] == start and s["end"] == end)
            ]

            self.highlight_spans()

        except tk.TclError:
            pass
