import tkinter as tk
from tkinter import messagebox
from utils import RE_ANY_TAG, RE_STRIP
from db import session
from services.metadata import parse_text_and_spans
from services.metadata import rebuild_text_from_spans



class Editor:
    def __init__(self, parent, state):
        self.state = state
        self.loading = False
        self.text = tk.Text(parent)
        self.text.pack(fill="both", expand=True)
        self.text.tag_config("tagged", background="lightyellow")
        self.text.bind("<<Modified>>", self.on_change)

    def on_change(self, event):
        if self.loading:
            return
    
        if self.text.edit_modified():
            # ✅ Optional: comment this out for now
            # self.state.spans = []
            # self.text.tag_remove("tagged", "1.0", tk.END)
    
            self.text.edit_modified(False)

    def load(self, memory):
        from services.metadata import parse_text_and_spans
    
        self.state.current_memory = memory
    
        self.loading = True  
    
        clean, spans = parse_text_and_spans(memory.text or "")
        self.state.spans = spans
    
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", clean)
    
        self.loading = False 
    
        self.highlight_spans()
    
        if hasattr(self.state, "metadata_panel"):
            self.state.metadata_panel.refresh()

    def save(self):
        m = self.state.current_memory
        if not m:
            return
            
        txt = self.text.get("1.0", tk.END)
        
        final = rebuild_text_from_spans(txt, list(self.state.spans))

        m.text = final
    
        if m.file_path:
            with open(m.file_path, "w", encoding="utf-8") as f:
                f.write(final)
    
        session.commit()

    def highlight_spans(self):
        import tkinter as tk
    
        # ✅ remove ALL previous highlights (VERY important)
        self.text.tag_remove("tagged", "1.0", tk.END)
    
        # ✅ define highlight style
        self.text.tag_config("tagged", background="#fff3b0")
    
        # ✅ apply spans
        for s in getattr(self.state, "spans", []):
            try:
                self.text.tag_add(
                    "tagged",
                    f"1.0+{s['start']}c",
                    f"1.0+{s['end']}c"
                )
            except Exception as e:
                print("Highlight error:", e)

    def add_tag(self, field, cho):
        import tkinter as tk
        from tkinter import messagebox
    
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
    
            start = int(self.text.count("1.0", sel_start)[0])
            end   = int(self.text.count("1.0", sel_end)[0])
    
            value = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
    
        except tk.TclError:
            messagebox.showerror("Error", "Select text first")
            return
    
        if not field or not cho:
            messagebox.showerror("Error", "Missing field or CHO")
            return
    
        span = {
            "start": start,
            "end": end,
            "field": field,
            "cho": cho,
            "value": value
        }
    
        for s in self.state.spans:
            if s["start"] == start and s["end"] == end:
                return
    
        self.state.spans.append(span)
    
        self.state.spans.sort(key=lambda s: s["start"])
    
        self.highlight_spans()
    
        if hasattr(self.state, "metadata_panel"):
            self.state.metadata_panel.refresh()


    def remove_tag(self):
        try:
            sel = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            clean = RE_STRIP.sub("", sel)

            self.text.delete(tk.SEL_FIRST, tk.SEL_LAST)
            self.text.insert(tk.INSERT, clean)

            self.highlight()

        except:
            pass
            
    def highlight_spans(self):
        import tkinter as tk
    
        # ✅ THIS LINE IS CRITICAL
        self.text.tag_remove("tagged", "1.0", tk.END)
    
        self.text.tag_config("tagged", background="#fff3b0")
    
        for s in self.state.spans:
            self.text.tag_add(
                "tagged",
                f"1.0+{s['start']}c",
                f"1.0+{s['end']}c"
            )
