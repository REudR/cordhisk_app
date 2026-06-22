import tkinter as tk
from tkinter import messagebox
from db import session, Memory

def ask_memory_full_form():
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
        tk.Label(win, text=label).grid(row=i, column=0)

        entry = tk.Text(win, height=3) if key == "dc:description" else tk.Entry(win)
        entry.grid(row=i, column=1)

        entries[key] = entry

    def ok():
        mid = entries["id"].get().strip()

        if not mid:
            messagebox.showerror("Error", "ID required")
            return

        if session.query(Memory).filter_by(custom_id=mid).first():
            messagebox.showerror("Error", "Duplicate ID")
            return

        metadata = {}
        for k, e in entries.items():
            if k == "id":
                continue
            val = e.get("1.0", "end").strip() if isinstance(e, tk.Text) else e.get().strip()
            if val:
                metadata[k] = val

        result["id"] = mid
        result["metadata"] = metadata
        win.destroy()

    tk.Button(win, text="OK", command=ok).grid(row=len(fields), column=0)
    tk.Button(win, text="Cancel", command=win.destroy).grid(row=len(fields), column=1)

    win.wait_window()
    return result
