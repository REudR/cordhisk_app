import tkinter as tk
from tkinter import ttk, messagebox
from db import session, CHO
from utils import MetadataType, METADATA_FIELDS, get_all_fields_by_type


class MetadataPanel:
    def __init__(self, parent, state, editor):
        self.state = state
        self.editor = editor

        frame = tk.LabelFrame(parent, text="Metadata")
        frame.pack(fill="x", pady=5)

        # Notebook for tabs: Memory vs CHO
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="x")

        # ===== TAB 1: MEMORY METADATA =====
        memory_tab = tk.Frame(notebook)
        notebook.add(memory_tab, text="Memory Metadata")

        self.memory_tree = ttk.Treeview(
            memory_tab,
            columns=("Field", "Value", "Index"),
            show="headings",
            height=4
        )
        for col in ("Field", "Value"):
            self.memory_tree.heading(col, text=col)
        self.memory_tree.column("Field", width=90, stretch=False)
        self.memory_tree.column("Value", width=150, stretch=False)
        self.memory_tree.pack(fill="x")
        self.memory_tree.bind("<Double-1>", self.edit_memory_metadata)
        self.memory_tree.bind("<<TreeviewSelect>>", self.on_select)

        # ===== TAB 2: CHO METADATA =====
        cho_tab = tk.Frame(notebook)
        notebook.add(cho_tab, text="CHO Metadata")

        self.cho_tree = ttk.Treeview(
            cho_tab,
            columns=("CHO", "Field", "Value", "Memory", "Index"),
            show="headings",
            height=4
        )
        for col in ("CHO", "Field", "Value", "Memory"):
            self.cho_tree.heading(col, text=col)
        self.cho_tree.column("CHO", width=70, stretch=False)
        self.cho_tree.column("Field", width=90, stretch=False)
        self.cho_tree.column("Value", width=150, stretch=False)
        self.cho_tree.column("Memory", width=80, stretch=False)
        self.cho_tree.pack(fill="x")
        self.cho_tree.bind("<Double-1>", self.edit_cho_metadata)
        self.cho_tree.bind("<<TreeviewSelect>>", self.on_select)

        # =========================
        # BUTTONS
        # =========================
        btns = tk.Frame(frame)
        btns.pack(fill="x")

        tk.Button(btns, text="Add Memory Meta", command=self.open_add_memory_dialog).pack(side="left", padx=2)
        tk.Button(btns, text="Add CHO Meta", command=self.open_add_cho_dialog).pack(side="left", padx=2)
        tk.Button(btns, text="Delete", command=self.delete).pack(side="left", padx=2)

    # =========================
    # REFRESH PANELS
    # =========================
    def refresh(self):
        """Refresh both memory and CHO metadata panels"""
        self.refresh_memory_metadata()
        self.refresh_cho_metadata()

    def refresh_memory_metadata(self):
        """Show only memory-intrinsic metadata"""
        self.memory_tree.delete(*self.memory_tree.get_children())
        
        for i, s in enumerate(self.state.spans):
            if s.get("type") == MetadataType.MEMORY.value:
                self.memory_tree.insert(
                    "",
                    "end",
                    values=(
                        s["field"],
                        s["value"],
                        i
                    )
                )
        
        self.memory_tree["displaycolumns"] = ("Field", "Value")

    def refresh_cho_metadata(self):
        """Show only CHO-linked metadata"""
        self.cho_tree.delete(*self.cho_tree.get_children())
        
        for i, s in enumerate(self.state.spans):
            if s.get("type") == MetadataType.CHO.value:
                self.cho_tree.insert(
                    "",
                    "end",
                    values=(
                        s.get("cho", ""),
                        s["field"],
                        s["value"],
                        getattr(self.state.current_memory, "custom_id", ""),
                        i
                    )
                )
        
        self.cho_tree["displaycolumns"] = ("CHO", "Field", "Value", "Memory")

    def show_cho_metadata(self, cho_id):
        """Show all metadata linked to a specific CHO"""
        from db import Memory
        from services.metadata import extract_metadata
    
        self.cho_tree.delete(*self.cho_tree.get_children())
        idx = 0
    
        for m in session.query(Memory):
            for md in extract_metadata(m.text):
                if md.get("type") == MetadataType.CHO.value and md.get("cho") == cho_id:
                    self.cho_tree.insert(
                        "",
                        "end",
                        values=(
                            md["cho"],
                            md["field"],
                            md["value"],
                            m.custom_id,
                            idx
                        )
                    )
                    idx += 1
    
        self.cho_tree["displaycolumns"] = ("CHO", "Field", "Value", "Memory")

    # =========================
    # DELETE METADATA
    # =========================
    def delete(self):
        """Delete selected metadata (from either tab)"""
        # Try CHO tree first
        selected = self.cho_tree.selection()
        tree = self.cho_tree
        if not selected:
            selected = self.memory_tree.selection()
            tree = self.memory_tree
        
        if not selected:
            return

        item = tree.item(selected[0])
        values = item["values"]

        if not values:
            return

        idx = int(values[-1])  # Index is always last column

        if 0 <= idx < len(self.state.spans):
            del self.state.spans[idx]

        self.editor.highlight_spans()
        self.refresh()

    # =========================
    # SELECT → SCROLL TO TEXT
    # =========================
    def on_select(self, event):
        """Highlight text in editor when metadata is selected"""
        widget = event.widget
        selected = widget.selection()
        if not selected:
            return

        item = widget.item(selected[0])
        values = item["values"]

        if not values:
            return

        idx = int(values[-1])  # Index is always last column

        if idx >= len(self.state.spans):
            return

        span = self.state.spans[idx]

        self.editor.text.see(f"1.0+{span['start']}c")
        self.editor.text.tag_remove("active_span", "1.0", "end")
        self.editor.text.tag_config("active_span", background="#ffcc66")
        self.editor.text.tag_add(
            "active_span",
            f"1.0+{span['start']}c",
            f"1.0+{span['end']}c"
        )

    # =========================
    # ADD MEMORY METADATA
    # =========================
    def open_add_memory_dialog(self):
        """Dialog to add memory-intrinsic metadata (WebResource fields)"""
        try:
            sel_start = self.editor.text.index("sel.first")
            sel_end = self.editor.text.index("sel.last")
        except:
            messagebox.showerror("Error", "Select text first")
            return

        dialog = tk.Toplevel()
        dialog.title("Add Memory Metadata")
        dialog.geometry("300x200")

        # Field selector (WebResource only)
        tk.Label(dialog, text="Field").pack()
        field_box = ttk.Combobox(dialog, values=METADATA_FIELDS["WebResource"]["fields"])
        field_box.pack()
        if METADATA_FIELDS["WebResource"]["fields"]:
            field_box.set(METADATA_FIELDS["WebResource"]["fields"][0])

        def submit():
            field = field_box.get()
            if not field:
                messagebox.showerror("Error", "Select field")
                return

            start = int(self.editor.text.count("1.0", sel_start)[0])
            end = int(self.editor.text.count("1.0", sel_end)[0])
            value = self.editor.text.get("sel.first", "sel.last")

            self.state.spans.append({
                "start": start,
                "end": end,
                "field": field,
                "value": value,
                "type": MetadataType.MEMORY.value
            })

            self.state.spans.sort(key=lambda s: s["start"])
            self.editor.highlight_spans()
            self.refresh()
            dialog.destroy()

        tk.Button(dialog, text="Add Tag", command=submit).pack(pady=10)

    # =========================
    # ADD CHO METADATA
    # =========================
    def open_add_cho_dialog(self):
        """Dialog to add CHO-linked metadata"""
        try:
            sel_start = self.editor.text.index("sel.first")
            sel_end = self.editor.text.index("sel.last")
        except:
            messagebox.showerror("Error", "Select text first")
            return

        dialog = tk.Toplevel()
        dialog.title("Add CHO Metadata")
        dialog.geometry("300x280")

        # CHO selector
        tk.Label(dialog, text="CHO").pack()
        cho_values = [c.custom_id for c in session.query(CHO)]
        cho_box = ttk.Combobox(dialog, values=cho_values)
        cho_box.pack()

        # Category selector
        tk.Label(dialog, text="Category").pack()
        categories = ["CHO", "Agent"]
        cat_box = ttk.Combobox(dialog, values=categories)
        cat_box.pack()

        # Field selector
        tk.Label(dialog, text="Field").pack()
        field_box = ttk.Combobox(dialog)
        field_box.pack()

        def update_fields(event):
            cat = cat_box.get()
            fields = METADATA_FIELDS.get(cat, {}).get("fields", [])
            field_box["values"] = fields
            if fields:
                field_box.set(fields[0])

        cat_box.bind("<<ComboboxSelected>>", update_fields)
        cat_box.set("CHO")
        update_fields(None)

        def submit():
            cho = cho_box.get()
            field = field_box.get()

            if not cho or not field:
                messagebox.showerror("Error", "Fill all fields")
                return

            start = int(self.editor.text.count("1.0", sel_start)[0])
            end = int(self.editor.text.count("1.0", sel_end)[0])
            value = self.editor.text.get("sel.first", "sel.last")

            self.state.spans.append({
                "start": start,
                "end": end,
                "field": field,
                "cho": cho,
                "value": value,
                "type": MetadataType.CHO.value
            })

            self.state.spans.sort(key=lambda s: s["start"])
            self.editor.highlight_spans()
            self.refresh()
            dialog.destroy()

        tk.Button(dialog, text="Add Tag", command=submit).pack(pady=10)

    # =========================
    # EDIT MEMORY METADATA
    # =========================
    def edit_memory_metadata(self, event):
        """Edit memory-intrinsic metadata"""
        item_id = self.memory_tree.identify_row(event.y)
        
        if not item_id:
            return
        
        self.memory_tree.selection_set(item_id)
        item = self.memory_tree.item(item_id)
        values = item["values"]
        
        if not values or len(values) < 3:
            return
        
        idx = int(values[-1])
        
        if idx >= len(self.state.spans):
            return
        
        span = self.state.spans[idx]
        
        dialog = tk.Toplevel()
        dialog.title("Edit Memory Metadata")
        dialog.geometry("300x200")
        
        tk.Label(dialog, text="Field").pack()
        field_box = ttk.Combobox(dialog, values=METADATA_FIELDS["WebResource"]["fields"])
        field_box.set(span["field"])
        field_box.pack()
        
        tk.Label(dialog, text="Value (read-only)").pack()
        val = tk.Entry(dialog)
        val.insert(0, span["value"])
        val.config(state="readonly")
        val.pack()
        
        def submit():
            span["field"] = field_box.get()
            self.editor.highlight_spans()
            self.refresh()
            dialog.destroy()
        
        tk.Button(dialog, text="Save", command=submit).pack(pady=10)

    # =========================
    # EDIT CHO METADATA
    # =========================
    def edit_cho_metadata(self, event):
        """Edit CHO-linked metadata"""
        item_id = self.cho_tree.identify_row(event.y)
        
        if not item_id:
            return
        
        self.cho_tree.selection_set(item_id)
        item = self.cho_tree.item(item_id)
        values = item["values"]
        
        if not values or len(values) < 5:
            return
        
        idx = int(values[-1])
        
        if idx >= len(self.state.spans):
            return
        
        span = self.state.spans[idx]
        
        dialog = tk.Toplevel()
        dialog.title("Edit CHO Metadata")
        dialog.geometry("300x250")
        
        tk.Label(dialog, text="CHO").pack()
        cho_values = [c.custom_id for c in session.query(CHO)]
        cho_box = ttk.Combobox(dialog, values=cho_values)
        cho_box.set(span["cho"])
        cho_box.pack()
        
        tk.Label(dialog, text="Field").pack()
        all_fields = get_all_fields_by_type(MetadataType.CHO)
        field_box = ttk.Combobox(dialog, values=all_fields)
        field_box.set(span["field"])
        field_box.pack()
        
        tk.Label(dialog, text="Value (read-only)").pack()
        val = tk.Entry(dialog)
        val.insert(0, span["value"])
        val.config(state="readonly")
        val.pack()
        
        def submit():
            span["cho"] = cho_box.get()
            span["field"] = field_box.get()
            self.editor.highlight_spans()
            self.refresh()
            dialog.destroy()
        
        tk.Button(dialog, text="Save", command=submit).pack(pady=10)
