import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from utils import MetadataType
from services.metadata import extract_metadata
from db import session, Memory


# =========================================================
# HELPERS
# =========================================================

def _get_id(obj):
    return getattr(obj, "custom_id", obj)


def _safe_text(value):
    if callable(value) or value is None:
        return None
    return str(value)


def _save_file(rdf_string, default_name):
    path = filedialog.asksaveasfilename(
        defaultextension=".rdf",
        initialfile=default_name,
        filetypes=[
            ("RDF files", "*.rdf"),
            ("All files", "*.*")
        ]
    )

    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(rdf_string)

        messagebox.showinfo("Export successful", f"Saved to:\n{path}")


def _indent(elem, level=0):
    """Pretty XML formatting"""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            _indent(e, level + 1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def _create_root():
    """Correct RDF namespaces"""
    return ET.Element("rdf:RDF", {
        "xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
        "xmlns:dcterms": "http://purl.org/dc/terms/",
        "xmlns:edm": "http://www.europeana.eu/schemas/edm/"
    })


# =========================================================
# UI: BUTTON SELECTION
# =========================================================

def _choose_export_mode():
    result = {"value": None}

    win = tk.Toplevel()
    win.title("Export CHO RDF")
    win.geometry("320x160")
    win.resizable(False, False)

    tk.Label(win, text="Choose export mode:", pady=10).pack()

    def choose_one():
        result["value"] = "one"
        win.destroy()

    def choose_all():
        result["value"] = "all"
        win.destroy()

    tk.Button(win, text="From ONE memory", command=choose_one, width=22).pack(pady=5)
    tk.Button(win, text="From ALL memories", command=choose_all, width=22).pack(pady=5)

    win.grab_set()
    win.wait_window()

    return result["value"]


# =========================================================
# ENTRY POINT
# =========================================================

def export_cho_rdf(cho):
    if not cho:
        messagebox.showerror("Error", "No CHO selected")
        return ""

    choice = _choose_export_mode()

    if choice == "one":
        return _export_cho_single_memory(cho)
    elif choice == "all":
        return _export_cho_all_memories(cho)

    return ""


# =========================================================
# SINGLE MEMORY EXPORT
# =========================================================

def _export_cho_single_memory(cho):
    cho_id = _get_id(cho)

    memories = session.query(Memory).all()
    ids = [m.custom_id for m in memories]

    selected = simpledialog.askstring(
        "Select Memory",
        "Enter Memory ID:\n\n" + "\n".join(ids[:30])
    )

    memory = next((m for m in memories if m.custom_id == selected), None)

    if not memory:
        messagebox.showerror("Error", "Memory not found")
        return ""

    root = _create_root()

    # CHO
    cho_desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/cho/{cho_id}"
    })

    ET.SubElement(cho_desc, "rdf:type").text = "edm:ProvidedCHO"
    ET.SubElement(cho_desc, "dc:identifier").text = _safe_text(cho_id)

    metadata = extract_metadata(memory.text or "")

    mem_uri = f"http://example.org/memory/{memory.custom_id}"
    contains = False

    cho_desc.append(ET.Comment("========================================"))
    cho_desc.append(ET.Comment(
        f" MEMORY | ID: {memory.custom_id} | Title: {memory.title or 'N/A'} "
    ))
    cho_desc.append(ET.Comment("========================================"))
    cho_desc[-1].tail = "\n\n"

    part = ET.SubElement(cho_desc, "dcterms:hasPart")

    block = ET.SubElement(part, "rdf:Description", {
        "rdf:about": mem_uri
    })

    for md in metadata:
        if md.get("type") == MetadataType.CHO.value and md.get("cho") == cho_id:
            field = md.get("field")
            value = _safe_text(md.get("value"))
            if field and value:
                contains = True
                ET.SubElement(cho_desc, field).text = value
                ET.SubElement(block, field).text = value

    web = ET.SubElement(block, "edm:WebResource")

    if memory.title:
        ET.SubElement(web, "dc:title").text = memory.title

    ET.SubElement(web, "dc:identifier").text = memory.custom_id

    ET.SubElement(block, "edm:isRelatedTo").set(
        "rdf:resource",
        f"http://example.org/cho/{cho_id}"
    )

    if contains:
        part.tail = "\n\n"
    else:
        cho_desc.remove(part)

    _indent(root)
    rdf = ET.tostring(root, encoding="unicode")
    _save_file(rdf, f"cho_{cho_id}_single.rdf")

    return rdf


# =========================================================
# ALL MEMORIES EXPORT
# =========================================================

def _export_cho_all_memories(cho):
    cho_id = _get_id(cho)

    root = _create_root()

    cho_desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/cho/{cho_id}"
    })

    ET.SubElement(cho_desc, "rdf:type").text = "edm:ProvidedCHO"
    ET.SubElement(cho_desc, "dc:identifier").text = _safe_text(cho_id)

    title = _safe_text(getattr(cho, "title", None))
    if title:
        ET.SubElement(cho_desc, "dc:title").text = title

    memories = session.query(Memory).all()
    seen = set()

    for memory in memories:

        metadata = extract_metadata(memory.text or "")
        mem_uri = f"http://example.org/memory/{memory.custom_id}"

        contains = False

        cho_desc.append(ET.Comment("========================================"))
        cho_desc.append(ET.Comment(
            f" MEMORY | ID: {memory.custom_id} | Title: {memory.title or 'N/A'} "
        ))
        cho_desc.append(ET.Comment("========================================"))
        cho_desc[-1].tail = "\n\n"

        part = ET.SubElement(cho_desc, "dcterms:hasPart")

        block = ET.SubElement(part, "rdf:Description", {
            "rdf:about": mem_uri
        })

        # metadata
        for md in metadata:
            if md.get("type") == MetadataType.CHO.value and md.get("cho") == cho_id:

                field = md.get("field")
                value = _safe_text(md.get("value"))

                if not field or not value:
                    continue

                contains = True

                if (field, value) not in seen:
                    ET.SubElement(cho_desc, field).text = value
                    seen.add((field, value))

                ET.SubElement(block, field).text = value

        # embedded WebResource
        web = ET.SubElement(block, "edm:WebResource")

        if memory.title:
            ET.SubElement(web, "dc:title").text = memory.title

        ET.SubElement(web, "dc:identifier").text = memory.custom_id

        ET.SubElement(block, "edm:isRelatedTo").set(
            "rdf:resource",
            f"http://example.org/cho/{cho_id}"
        )

        if contains:
            part.tail = "\n\n"
        else:
            cho_desc.remove(part)

    _indent(root)
    rdf = ET.tostring(root, encoding="unicode")
    _save_file(rdf, f"cho_{cho_id}_all.rdf")

    return rdf


# =========================================================
# MEMORY EXPORT
# =========================================================

def export_memory_rdf(memory):
    if not memory:
        messagebox.showerror("Error", "No memory selected")
        return ""

    mid = _get_id(memory)

    root = _create_root()

    desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/memory/{mid}"
    })

    ET.SubElement(desc, "rdf:type").text = "edm:WebResource"
    ET.SubElement(desc, "dc:identifier").text = mid

    if memory.title:
        ET.SubElement(desc, "dc:title").text = memory.title

    metadata = extract_metadata(memory.text or "")
    cho_refs = set()

    for md in metadata:
        if md.get("type") == MetadataType.MEMORY.value:
            ET.SubElement(desc, md["field"]).text = _safe_text(md["value"])

    for md in metadata:
        if md.get("type") == MetadataType.CHO.value and md.get("cho"):
            cho_refs.add(md["cho"])

    for cho_id in cho_refs:
        ET.SubElement(desc, "edm:isRelatedTo").set(
            "rdf:resource",
            f"http://example.org/cho/{cho_id}"
        )

    _indent(root)
    rdf = ET.tostring(root, encoding="unicode")
    _save_file(rdf, f"memory_{mid}.rdf")

    return rdf
