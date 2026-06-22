import tkinter as tk
from tkinter import ttk, messagebox
from db import session, CHO


class MetadataPanel:
    def __init__(self, parent, state, editor):
        self.state = state
        self.editor = editor

        frame = tk.LabelFrame(parent, text="Metadata")
        frame.pack(fill="x", pady=5)

        # =========================
        # TREEVIEW
        # =========================
        self.tree = ttk.Treeview(
            frame,
            columns=("CHO", "Field", "Value", "Index"),
            show="headings",
            height=6
        )

        for col in ("CHO", "Field", "Value"):
            self.tree.heading(col, text=col)

        self.tree.pack(fill="x")

        # ✅ CORRECT bindings
        self.tree.bind("<Double-1>", self.edit)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # =========================
        # BUTTONS
        # =========================
        btns = tk.Frame(frame)
        btns.pack(fill="x")

        #tk.Button(btns, text="Add", command=self.open_add_dialog).pack(side="left")
        #tk.Button(btns, text="Delete", command=self.delete).pack(side="left")

    # =========================
    # REFRESH PANEL
    # =========================
    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        for i, s in enumerate(self.state.spans):
            self.tree.insert(
                "",
                "end",
                values=(s["cho"], s["field"], s["value"], i)
            )

        # hide index column
        self.tree["displaycolumns"] = ("CHO", "Field", "Value")

    # =========================
    # DELETE METADATA
    # =========================
    def delete(self):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        values = item["values"]

        if len(values) < 4:
            return

        idx = int(values[3])

        if 0 <= idx < len(self.state.spans):
            del self.state.spans[idx]

        self.editor.highlight_spans()
        self.refresh()

    # =========================
    # SELECT → SCROLL TO TEXT
    # =========================
    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        values = item["values"]

        if len(values) < 4:
            return

        idx = int(values[3])

        if idx >= len(self.state.spans):
            return

        span = self.state.spans[idx]

        start = f"1.0+{span['start']}c"

        self.editor.text.see(start)

        self.editor.text.tag_remove("active_span", "1.0", "end")
        self.editor.text.tag_config("active_span", background="#ffcc66")

        self.editor.text.tag_add(
            "active_span",
            f"1.0+{span['start']}c",
            f"1.0+{span['end']}c"
        )

    # =========================
    # ADD METADATA (DIALOG)
    # =========================
    def open_add_dialog(self):
        try:
            sel_start = self.editor.text.index("sel.first")
            sel_end = self.editor.text.index("sel.last")
        except:
            messagebox.showerror("Error", "Select text first")
            return

        dialog = tk.Toplevel()
        dialog.title("Add Metadata")
        dialog.geometry("300x220")

        # CHO selector
        tk.Label(dialog, text="CHO").pack()
        cho_values = [c.custom_id for c in session.query(CHO)]

        cho_box = ttk.Combobox(dialog, values=cho_values)
        cho_box.pack()

        # Category selector
        tk.Label(dialog, text="Category").pack()

        categories = ["CHO", "Agent", "WebResource", "Place"]
        cat_box = ttk.Combobox(dialog, values=categories)
        cat_box.pack()

        # Field selector
        tk.Label(dialog, text="Field").pack()

        field_box = ttk.Combobox(dialog)
        field_box.pack()

        # =========================
        # FIELD DICTIONARY
        # =========================
        FIELDS = {
            "CHO": [
                "dc:contributor","dc:coverage","dc:creator","dc:date",
                "dc:description","dc:format","dc:language","dc:publisher",
                "dc:source","dc:subject","dc:title","dc:type",
                "dcterms:created","dcterms:extent","dcterms:issued",
                "dcterms:medium","dcterms:provenance","dcterms:spatial",
                "dcterms:tableOfContents","dcterms:temporal"
            ],
            "Agent": [
                "oaf:name","rdaGr2:biographicalInformation",
                "rdaGr2:dateOfBirth","rdaGr2:dateOfDeath",
                "rdaGr2:dateOfEstablishment","rdaGr2:dateOfTermination",
                "rdaGr2:gender","rdaGr2:placeOfBirth",
                "rdaGr2:placeOfDeath","rdaGr2:professionOrOccupation"
            ],
            "WebResource": [],
            "Place": []
        }

        def update_fields(event):
            cat = cat_box.get()
            fields = FIELDS.get(cat, [])

            field_box["values"] = fields

            if fields:
                field_box.set(fields[0])
            else:
                field_box.set("")

        cat_box.bind("<<ComboboxSelected>>", update_fields)

        cat_box.set("CHO")
        update_fields(None)

        # =========================
        # SUBMIT
        # =========================
        def submit():
            cho = cho_box.get()
            field = field_box.get()

            if not cho or not field:
                messagebox.showerror("Error", "Fill all fields")
                return

            start = int(self.editor.text.count("1.0", sel_start)[0])
            end   = int(self.editor.text.count("1.0", sel_end)[0])

            value = self.editor.text.get("sel.first", "sel.last")

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

            dialog.destroy()

        tk.Button(dialog, text="Add Tag", command=submit).pack(pady=10)

    # =========================
    # EDIT METADATA
    # =========================
    def edit(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        values = item["values"]

        if len(values) < 4:
            return

        idx = int(values[3])

        if idx >= len(self.state.spans):
            return

        span = self.state.spans[idx]

        dialog = tk.Toplevel()
        dialog.title("Edit Metadata")
        dialog.geometry("300x220")

        # CHO selector
        tk.Label(dialog, text="CHO").pack()
        cho_values = [c.custom_id for c in session.query(CHO)]

        cho_box = ttk.Combobox(dialog, values=cho_values)
        cho_box.set(span["cho"])
        cho_box.pack()

        # Field selector
        tk.Label(dialog, text="Field").pack()

        all_fields = [
            "dc:contributor","dc:coverage","dc:creator","dc:date",
            "dc:description","dc:format","dc:language","dc:publisher",
            "dc:source","dc:subject","dc:title","dc:type",
            "dcterms:created","dcterms:extent","dcterms:issued",
            "dcterms:medium","dcterms:provenance","dcterms:spatial",
            "dcterms:tableOfContents","dcterms:temporal",
            "oaf:name","rdaGr2:biographicalInformation",
            "rdaGr2:dateOfBirth","rdaGr2:dateOfDeath",
            "rdaGr2:dateOfEstablishment","rdaGr2:dateOfTermination",
            "rdaGr2:gender","rdaGr2:placeOfBirth",
            "rdaGr2:placeOfDeath","rdaGr2:professionOrOccupation"
        ]

        field_box = ttk.Combobox(dialog, values=all_fields)
        field_box.set(span["field"])
        field_box.pack()

        # Value (read-only)
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