from tkinter import simpledialog, Toplevel, Text
from db import session, Memory

def search():
    term = simpledialog.askstring("Search", "Text")
    if not term:
        return

    results = session.query(Memory).filter(
        Memory.text.ilike(f"%{term}%")
    ).all()

    win = Toplevel()
    text = Text(win)
    text.pack(fill="both", expand=True)

    for m in results:
        text.insert("end", f"{m.custom_id}\n")