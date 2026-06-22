import xml.etree.ElementTree as ET
from tkinter import filedialog
from db import session, Memory
from services.metadata import extract_metadata

def export_cho_rdf(cho_id):
    import xml.etree.ElementTree as ET
    from tkinter import filedialog, messagebox
    from db import session, Memory
    from services.metadata import extract_metadata

    if not cho_id:
        messagebox.showerror("Error", "No CHO selected")
        return

    root = ET.Element("rdf:RDF")
    found = False

    for m in session.query(Memory):

        # ✅ filter metadata for THIS memory + THIS cho
        meta = [
            md for md in extract_metadata(m.text)
            if md["cho"] == cho_id
        ]

        if not meta:
            continue

        found = True

        # ✅ ONE block per memory
        desc = ET.SubElement(root, "rdf:Description")

        # ✅ (optional but useful) add memory id
        desc.set("memory", m.custom_id)

        for md in meta:
            ET.SubElement(desc, md["field"]).text = md["value"]

    if not found:
        messagebox.showinfo("Info", "No metadata found for this CHO")
        return

    path = filedialog.asksaveasfilename(defaultextension=".xml")
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(ET.tostring(root, encoding="unicode"))

def export_memory_rdf(memory):
    import xml.etree.ElementTree as ET
    from tkinter import filedialog, messagebox
    from services.metadata import extract_metadata

    if not memory:
        messagebox.showerror("Error", "No memory selected or loaded")
        return

    metadata = extract_metadata(memory.text)

    if not metadata:
        messagebox.showinfo("Info", "No metadata in memory")
        return

    root = ET.Element("rdf:RDF")

    # ✅ group by CHO inside this memory
    grouped = {}

    for md in metadata:
        grouped.setdefault(md["cho"], []).append(md)

    for cho_id, items in grouped.items():

        # ✅ ONE block per CHO
        desc = ET.SubElement(root, "rdf:Description")

        # ✅ attach CHO id
        desc.set("cho", cho_id)

        for md in items:
            ET.SubElement(desc, md["field"]).text = md["value"]

    path = filedialog.asksaveasfilename(defaultextension=".xml")
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(ET.tostring(root, encoding="unicode"))
