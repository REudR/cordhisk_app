import tkinter as tk
from tkinter import ttk, messagebox
from db import session, CHO
from utils import (
    MetadataType,
    METADATA_FIELDS,
    get_all_fields_by_type,
    field_to_display,
    display_to_field
)


class MetadataPanel:
    def __init__(self, parent, state, editor):
        self.state = state
        self.editor = editor

        self.memory_row_map = {}
        self.cho_row_map = {}

        frame = tk.LabelFrame(parent, text="Metadata embedded in the Memory")
        frame.pack(fill="x", pady=5)

        notebook = ttk.Notebook(frame)
        notebook.pack(fill="x")

        # ===== MEMORY TAB
        memory_tab = tk.Frame(notebook)
        notebook.add(memory_tab, text="Memory Metadata")

        self.memory_tree = ttk.Treeview(
            memory_tab,
            columns=("Field", "Value"),
            show="headings",
            height=4
        )
        self.memory_tree.heading("Field", text="Field")
        self.memory_tree.heading("Value", text="Value")
        self.memory_tree.pack(fill="both", expand=True)
        self.memory_tree.bind("<Double-1>", self.edit_memory_metadata)

        # ===== CHO TAB
        cho_tab = tk.Frame(notebook)
        cho_tab.pack_propagate(False)
        notebook.add(cho_tab, text="CHO Metadata")

        self.cho_tree = ttk.Treeview(
            cho_tab,
            columns=("CHO", "Field", "Value"),
            show="headings",
            height=4
        )
        for col in ("CHO", "Field", "Value"):
            self.cho_tree.heading(col, text=col)
            self.cho_tree.column("CHO", width=80, stretch=False)
            self.cho_tree.column("Field", width=120, stretch=False)
            self.cho_tree.column("Value", width=300, stretch=True)

        self.cho_tree.pack(fill="both", expand=True)
        self.cho_tree.bind("<Double-1>", self.edit_cho_metadata)

        # buttons
        btns = tk.Frame(frame)
        btns.pack(fill="x")

        tk.Button(btns, text="Add Memory Meta", command=self.open_add_memory_dialog).pack(side="left")
        tk.Button(btns, text="Add CHO Meta", command=self.open_add_cho_dialog).pack(side="left")
        tk.Button(btns, text="Delete", command=self.delete).pack(side="left")

    # =========================
    # REFRESH (ONLY FROM SPANS ✅)
    # =========================
    def refresh(self):
        self.memory_tree.delete(*self.memory_tree.get_children())
        self.memory_row_map = {}

        for span in self.state.spans:
            if span.get("type") == MetadataType.MEMORY.value:
                item = self.memory_tree.insert("", "end",
                    values=(span["field"], span["value"]))
                self.memory_row_map[item] = span

        self.cho_tree.delete(*self.cho_tree.get_children())
        self.cho_row_map = {}

        for span in self.state.spans:
            if span.get("type") == MetadataType.CHO.value:
                item = self.cho_tree.insert(
                    "",
                    "end",
                    values=(span.get("cho"), span["field"], span["value"])
                )
                self.cho_row_map[item] = span

    # =========================
    # REBUILD BLOCK + SAVE ✅
    # =========================
    def rebuild_and_save(self):
        memory = self.state.current_memory
        if not memory:
            return

        # ✅ use editor.save() → ensures file sync
        self.editor.save()

        # ✅ reload to re-parse cleanly
        self.editor.load(memory)

    # =========================
    # ADD MEMORY META
    # =========================
    def open_add_memory_dialog(self):
        try:
            text = self.editor.text.get("sel.first", "sel.last")
            start = int(self.editor.text.count("1.0", "sel.first")[0])
        except:
            messagebox.showerror("Error", "Select text first")
            return

        dialog = tk.Toplevel()

        field_box = ttk.Combobox(dialog, values=METADATA_FIELDS["WebResource"]["fields"])
        field_box.pack()

        def submit():
            self.state.spans.append({
                "start": start,
                "end": start + len(text),
                "field": field_box.get(),
                "value": text,
                "type": MetadataType.MEMORY.value
            })

            self.rebuild_and_save()
            self.refresh()
            dialog.destroy()

        tk.Button(dialog, text="Add", command=submit).pack()

    # =========================
    # ADD CHO META
    # =========================
    def open_add_cho_dialog(self):
        try:
            text = self.editor.text.get("sel.first", "sel.last")
            start = int(self.editor.text.count("1.0", "sel.first")[0])
        except:
            messagebox.showerror("Error", "Select text first")
            return
    
        dialog = tk.Toplevel()
        dialog.title("Add CHO Metadata")
        dialog.geometry("320x220")
    
        # =========================
        # CHO
        # =========================
        tk.Label(dialog, text="CHO").pack()
    
        cho_box = ttk.Combobox(
            dialog,
            values=[c.custom_id for c in session.query(CHO)]
        )
        cho_box.pack()
    
        # =========================
        # FIELD (ALIASES + CATEGORY ✅)
        # =========================

        tk.Label(dialog, text="Field").pack()

        # ✅ Get all CHO-related fields
        fields = get_all_fields_by_type(MetadataType.CHO)
        
        # ✅ Convert to user-friendly display
        displays = [field_to_display(f) for f in fields]
        
        field_box = ttk.Combobox(dialog, values=displays)
        field_box["state"] = "readonly"   # ✅ important for correct rendering
        field_box.pack()
        
        # ✅ Optional default selection
        if displays:
            field_box.set(displays[0])
    
        # =========================
        # SUBMIT
        # =========================
        def submit():
            display = field_box.get()
            real_field = display_to_field(display, fields)
            
            if not real_field:
                messagebox.showerror("Error", "Invalid field")
                return

            real_field = display_to_field(display, fields)
    
            if not real_field:
                messagebox.showerror("Error", "Invalid field")
                return
    
            cho = cho_box.get()
            if not cho:
                messagebox.showerror("Error", "Select a CHO")
                return
    

            self.state.spans.append({
                "start": start,
                "end": start + len(text),
                "field": real_field,
                "value": text,
                "cho": cho,
                "type": MetadataType.CHO.value
            })
            
            self.editor.highlight_spans()
            self.editor.save()
            self.refresh()
            dialog.destroy()

        tk.Button(dialog, text="Add", command=submit).pack(pady=10)
    # =========================
    # EDIT MEMORY
    # =========================
    def edit_memory_metadata(self, event):
        item = self.memory_tree.identify_row(event.y)
        if not item:
            return

        span = self.memory_row_map.get(item)
        if not span:
            return

        dialog = tk.Toplevel()

        field_box = ttk.Combobox(dialog,
            values=METADATA_FIELDS["WebResource"]["fields"])
        field_box.set(span["field"])
        field_box.pack()

        val = tk.Entry(dialog)
        val.insert(0, span["value"])
        val.pack()

        def submit():
            span["field"] = field_box.get()
            span["value"] = val.get()

            self.rebuild_and_save()
            self.refresh()
            dialog.destroy()

        tk.Button(dialog, text="Save", command=submit).pack()

    # =========================
    # EDIT CHO
    # =========================
    def edit_cho_metadata(self, event):
        item = self.cho_tree.identify_row(event.y)
        if not item:
            return

        span = self.cho_row_map.get(item)
        if not span:
            return

        dialog = tk.Toplevel()

        field_box = ttk.Combobox(dialog,
            values=get_all_fields_by_type(MetadataType.CHO))
        field_box.set(span["field"])
        field_box.pack()

        def submit():
            span["field"] = field_box.get()
            self.editor.save()
            self.refresh()
            dialog.destroy()

        tk.Button(dialog, text="Save", command=submit).pack()

    # =========================
    # DELETE
    # =========================
    def delete(self):
        selected = self.memory_tree.selection() or self.cho_tree.selection()
        if not selected:
            return

        item = selected[0]
        span = self.memory_row_map.get(item) or self.cho_row_map.get(item)

        if span in self.state.spans:
            self.state.spans.remove(span)

        self.rebuild_and_save()
        self.refresh()