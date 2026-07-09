import tkinter as tk
from tkinter import messagebox
from db import session, Memory


def ask_memory_full_form(initial_metadata=None, initial_id=None, parent=None):
    initial = initial_metadata or {}
    result = {}

    if parent is not None:
        root = parent
    else:
        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()  

    win = tk.Toplevel(root)
    win.title("Memory")
    win.transient(root)
    win.grab_set()
    win.focus_set()

    # =========================
    # SAFE CLOSE
    # =========================
    def on_close():
        try:
            win.grab_release()
        except Exception:
            pass

        if win.winfo_exists():
            win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close)

    # =========================
    # FORM FIELDS
    # =========================
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

        if key == "dc:description":
            entry = tk.Text(win, height=3, width=40)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entry.insert("1.0", initial.get(key, ""))
        else:
            entry = tk.Entry(win, width=40)
            entry.grid(row=i, column=1, padx=5, pady=2)

            if key == "id":
                entry.insert(0, initial_id or "")
            else:
                entry.insert(0, initial.get(key, ""))

        entries[key] = entry

    # =========================
    # OK ACTION
    # =========================
    def ok():
        mid = entries["id"].get().strip()

        if not mid:
            messagebox.showerror("Error", "ID required", parent=win)
            return

        existing = session.query(Memory).filter_by(custom_id=mid).first()

        if existing and mid != initial_id:
            messagebox.showerror("Error", "Duplicate ID", parent=win)
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

        on_close()

    # =========================
    # BUTTONS
    # =========================
    tk.Button(win, text="OK", command=ok).grid(
        row=len(fields), column=0, padx=5, pady=5
    )

    tk.Button(win, text="Cancel", command=on_close).grid(
        row=len(fields), column=1, padx=5, pady=5
    )

    win.wait_window()

    return result if result else None