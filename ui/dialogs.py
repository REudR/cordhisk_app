import tkinter as tk
from tkinter import messagebox
from db import session, Memory


def ask_memory_full_form(initial=None):
    if initial is None:
        initial = {}

    result = {}
    win = tk.Toplevel()
    win.title("New Memory")
    win.grab_set()

    fields = [
        ("ID", "id"),
        ("dc:title", "dc:title"),
        ("dc:creator", "dc:creator"),
        ("dc:date", "dc:date"),
        ("dc:subject", "dc:subject"),
        ("dc:description", "dc:description"),
    ]

    entries = {}

    for i, (label, key) in enumerate(fields):
        tk.Label(win, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=2)

        # Use Text widget for description
        if key == "dc:description":
            entry = tk.Text(win, height=3, width=40)
            entry.grid(row=i, column=1, padx=5, pady=2)

            # ✅ PREFILL Text widget
            if key in initial:
                entry.insert("1.0", initial.get(key, ""))

        else:
            entry = tk.Entry(win, width=40)
            entry.grid(row=i, column=1, padx=5, pady=2)

            # ✅ PREFILL Entry widget
            entry.insert(0, initial.get(key, ""))

        entries[key] = entry

    # =========================
    # SUBMIT
    # =========================
    def ok():
        mid = entries["id"].get().strip()

        if not mid:
            messagebox.showerror("Error", "ID required")
            return

        # ✅ Only check duplicates if it's a NEW ID
        # (important: allows prefilling without false positives)
        existing = session.query(Memory).filter_by(custom_id=mid).first()
        if "id" not in initial and existing:
            messagebox.showerror("Error", "Duplicate ID")
            return

        metadata = {}

        for k, e in entries.items():
            if k == "id":
                continue

            if isinstance(e, tk.Text):
                val = e.get("1.0", "end").strip()
            else:
                val = e.get().strip()

            if val:
                metadata[k] = val

        result["id"] = mid
        result["metadata"] = metadata

        win.destroy()

    # =========================
    # BUTTONS
    # =========================
    tk.Button(win, text="OK", command=ok).grid(
        row=len(fields), column=0, padx=5, pady=5
    )

    tk.Button(win, text="Cancel", command=win.destroy).grid(
        row=len(fields), column=1, padx=5, pady=5
    )

    win.wait_window()

    return result if result else None