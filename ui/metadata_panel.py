import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from services.metadata import extract_metadata
from db import session, CHO

class MetadataPanel:
    def __init__(self, parent, state, editor):
        import tkinter as tk
        from tkinter import ttk

        self.state = state
        self.editor = editor

        frame = tk.LabelFrame(parent, text="Metadata")
        frame.pack(fill="x", pady=5)

        self.tree = ttk.Treeview(
            frame,
            columns=("CHO", "Field", "Value"),
            show="headings",
            height=6
        )

        for col in ("CHO", "Field", "Value"):
            self.tree.heading(col, text=col)

        self.tree.pack(fill="x")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Buttons
        btns = tk.Frame(frame)
        btns.pack(fill="x")

        tk.Button(btns, text="Add", command=self.add).pack(side="left")
        tk.Button(btns, text="Delete", command=self.delete).pack(side="left")

    # =========================
    # REFRESH PANEL
    # =========================
    
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
    
        for i, s in enumerate(self.state.spans):
            self.tree.insert(
                "",
                "end",
                values=(s["cho"], s["field"], s["value"]),
                iid=str(i) 
            )
    # =========================
    # ADD METADATA
    # =========================
    def add(self):
        import tkinter as tk
        from tkinter import simpledialog, messagebox
    
        try:
            sel_start = self.editor.text.index(tk.SEL_FIRST)
            sel_end = self.editor.text.index(tk.SEL_LAST)
    
            start = int(self.editor.text.count("1.0", sel_start)[0])
            end   = int(self.editor.text.count("1.0", sel_end)[0])
    
        except:
            messagebox.showerror("Error", "Select text first")
            return
    
        cho = simpledialog.askstring("CHO", "Enter CHO ID")
        if not cho:
            return
    
        field = self.state.current_field
        value = self.editor.text.get(tk.SEL_FIRST, tk.SEL_LAST)
    
        self.state.spans.append({
            "start": start,
            "end": end,
            "field": field,
            "cho": cho,
            "value": value
        })
    
        self.state.spans.sort(key=lambda s: s["start"])
        self.editor.highlight_spans()
        self.refresh()


    # =========================
    # DELETE METADATA
    # =========================
    
    def delete(self):
        selected = self.tree.selection()
        if not selected:
            return
    
        # ✅ retrieve span index directly
        idx = int(selected[0])
    
        if 0 <= idx < len(self.state.spans):
            del self.state.spans[idx]
    
        # ✅ update UI
        self.editor.highlight_spans()
        self.refresh()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
    
        idx = self.tree.index(selected[0])
    
        if idx >= len(self.state.spans):
            return
    
        span = self.state.spans[idx]
    
        # scroll text to span
        start = f"1.0+{span['start']}c"
    
        self.editor.text.see(start)
    
        # optional: temporary highlight
        self.editor.text.tag_remove("active_span", "1.0", "end")
        self.editor.text.tag_config("active_span", background="#ffcc66")
    
        self.editor.text.tag_add(
            "active_span",
            f"1.0+{span['start']}c",
            f"1.0+{span['end']}c"
        )