import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from services.metadata import extract_metadata
from db import session, CHO

class MetadataPanel:
    def __init__(self, parent, state, editor):
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

        btns = tk.Frame(frame)
        btns.pack(fill="x")

        tk.Button(btns, text="Add", command=self.add).pack(side="left")
        tk.Button(btns, text="Delete", command=self.delete).pack(side="left")

    # =========================
    # REFRESH PANEL
    # =========================
    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        mem = self.state.current_memory
        if not mem:
            return

        metadata = extract_metadata(mem.text)

        for md in metadata:
            self.tree.insert(
                "",
                "end",
                values=(md["cho"], md["field"], md["value"])
            )

    # =========================
    # ADD METADATA
    # =========================
    def add(self):
        mem = self.state.current_memory
        if not mem:
            messagebox.showerror("Error", "No memory selected")
            return

        # ✅ CHO selection (improved)
        chos = [c.custom_id for c in session.query(CHO)]

        if not chos:
            messagebox.showerror("Error", "No CHOs available")
            return

        cho = simpledialog.askstring(
            "CHO",
            f"Enter CHO ID:\nAvailable: {', '.join(chos)}"
        )
        if not cho:
            return

        # ✅ Field (from toolbar if available)
        field = getattr(self.state, "current_field", None)
        if not field:
            field = simpledialog.askstring("Field", "Enter metadata field (e.g. dc:title)")
            if not field:
                return

        # ✅ Value
        value = simpledialog.askstring("Value", "Enter metadata value")
        if not value:
            return

        tag = f'<{field} cho="{cho}">{value}</{field}>'

        self.editor.text.insert("end", "\n" + tag)
        self.editor.highlight()

        self.refresh()

    # =========================
    # DELETE METADATA
    # =========================
    def delete(self):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        cho, field, value = item["values"]

        mem = self.state.current_memory
        if not mem:
            return

        tag = f'<{field} cho="{cho}">{value}</{field}>'

        txt = self.editor.text.get("1.0", "end")
        txt = txt.replace(tag, "")

        self.editor.text.delete("1.0", "end")
        self.editor.text.insert("1.0", txt)

        self.editor.highlight()
        self.refresh()