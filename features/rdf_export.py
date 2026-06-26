import xml.etree.ElementTree as ET
from tkinter import filedialog, messagebox, simpledialog

from utils import MetadataType
from services.metadata import extract_metadata
from db import session, Memory


# =========================================================
# HELPERS
# =========================================================

def _get_id(obj):
    """Return custom_id if object, else assume string"""
    return getattr(obj, "custom_id", obj)


def _safe_text(value):
    """Ensure XML-safe text"""
    if callable(value) or value is None:
        return None
    return str(value)


def _save_file(rdf_string, default_name):
    """Save RDF file using a dialog"""
    path = filedialog.asksaveasfilename(
        defaultextension=".rdf",
        initialfile=default_name,
        filetypes=[
            ("RDF files", "*.rdf"),
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ]
    )

    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(rdf_string)

        messagebox.showinfo("Export successful", f"Saved to:\n{path}")


def _indent(elem, level=0):
    """
    Pretty-print XML (human-readable)
    """
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
    """Create RDF root with namespaces"""
    return ET.Element("rdf:RDF", {
        "xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
        "xmlns:dcterms": "http://purl.org/dc/terms/",
        "xmlns:edm": "http://www.europeana.eu/schemas/edm/"
    })


# =========================================================
# ENTRY POINT
# =========================================================

def export_cho_rdf(cho):
    """
    Ask user how to export CHO RDF
    """
    if not cho:
        messagebox.showerror("Error", "No CHO selected")
        return ""

    choice = simpledialog.askstring(
        "Export CHO RDF",
        "Choose export mode:\n\n"
        "1 = From ONE memory\n"
        "2 = From ALL memories (grouped)"
    )

    if choice == "1":
        return _export_cho_single_memory(cho)
    elif choice == "2":
        return _export_cho_all_memories(cho)
    else:
        return ""


# =========================================================
# OPTION 1 — SINGLE MEMORY
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

    # -----------------------------
    # CHO node
    # -----------------------------
    cho_desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/cho/{cho_id}"
    })

    ET.SubElement(cho_desc, "rdf:type").text = "edm:ProvidedCHO"
    ET.SubElement(cho_desc, "dc:identifier").text = _safe_text(cho_id)

    metadata = extract_metadata(memory.text or "")

    for md in metadata:
        if md.get("type") == MetadataType.CHO.value and md.get("cho") == cho_id:
            field = md.get("field")
            value = _safe_text(md.get("value"))
            if field and value:
                ET.SubElement(cho_desc, field).text = value

    # -----------------------------
    # Memory node
    # -----------------------------
    mem_uri = f"http://example.org/memory/{memory.custom_id}"

    ET.SubElement(cho_desc, "dcterms:hasPart").set("rdf:resource", mem_uri)

    mem_desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": mem_uri
    })

    ET.SubElement(mem_desc, "rdf:type").text = "edm:WebResource"
    ET.SubElement(mem_desc, "dc:identifier").text = memory.custom_id

    title = _safe_text(memory.title)
    if title:
        ET.SubElement(mem_desc, "dc:title").text = title

    ET.SubElement(mem_desc, "edm:isRelatedTo").set(
        "rdf:resource",
        f"http://example.org/cho/{cho_id}"
    )

    # -----------------------------
    # Output
    # -----------------------------
    _indent(root)
    rdf_string = ET.tostring(root, encoding="unicode")

    _save_file(rdf_string, f"cho_{cho_id}_single.rdf")
    return rdf_string


# =========================================================
# OPTION 2 — ALL MEMORIES (GROUPED + LINKED)
# =========================================================

def _export_cho_all_memories(cho):
    cho_id = _get_id(cho)

    root = _create_root()

    # -----------------------------
    # CHO node
    # -----------------------------
    cho_desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/cho/{cho_id}"
    })

    ET.SubElement(cho_desc, "rdf:type").text = "edm:ProvidedCHO"
    ET.SubElement(cho_desc, "dc:identifier").text = _safe_text(cho_id)

    # optional object title
    title = _safe_text(getattr(cho, "title", None))
    if title:
        ET.SubElement(cho_desc, "dc:title").text = title

    memories = session.query(Memory).all()
    linked_memories = []
    seen_global = set()  # avoid duplicate metadata

    # -----------------------------
    # Process each memory
    # -----------------------------
    for memory in memories:
    
        metadata = extract_metadata(memory.text or "")
        contains_cho = False
    
        mem_uri = f"http://example.org/memory/{memory.custom_id}"
    
        # ✅ HUMAN-READABLE COMMENT (NEW)
        comment_text = f" MEMORY | ID: {memory.custom_id} | Title: {memory.title or 'N/A'} "
        cho_desc.append(ET.Comment(comment_text))
    
        # -------------------------
        # Create memory block (provenance)
        # -------------------------
        part = ET.SubElement(cho_desc, "dcterms:hasPart")
        block = ET.SubElement(part, "rdf:Description", {
            "rdf:about": mem_uri
        })
    
        for md in metadata:
            if md.get("type") == MetadataType.CHO.value and md.get("cho") == cho_id:
    
                field = md.get("field")
                value = _safe_text(md.get("value"))
    
                if not field or not value:
                    continue
    
                contains_cho = True
    
                if (field, value) not in seen_global:
                    ET.SubElement(cho_desc, field).text = value
                    seen_global.add((field, value))
    
                ET.SubElement(block, field).text = value
    
        if contains_cho:
            linked_memories.append(memory)
        else:
            cho_desc.remove(part)

        # -------------------------
        # Create memory block (provenance)
        # -------------------------
        part = ET.SubElement(cho_desc, "dcterms:hasPart")
        block = ET.SubElement(part, "rdf:Description", {
            "rdf:about": mem_uri
        })

        for md in metadata:
            if md.get("type") == MetadataType.CHO.value and md.get("cho") == cho_id:

                field = md.get("field")
                value = _safe_text(md.get("value"))

                if not field or not value:
                    continue

                contains_cho = True

                # deduplicate globally
                if (field, value) not in seen_global:
                    ET.SubElement(cho_desc, field).text = value
                    seen_global.add((field, value))

                # keep provenance (memory-level)
                ET.SubElement(block, field).text = value

        if contains_cho:
            linked_memories.append(memory)
        else:
            cho_desc.remove(part)

    # -----------------------------
    # Declare memory nodes
    # -----------------------------
    for memory in linked_memories:

        mem_uri = f"http://example.org/memory/{memory.custom_id}"

        mem_desc = ET.SubElement(root, "rdf:Description", {
            "rdf:about": mem_uri
        })

        ET.SubElement(mem_desc, "rdf:type").text = "edm:WebResource"
        ET.SubElement(mem_desc, "dc:identifier").text = memory.custom_id

        title = _safe_text(memory.title)
        if title:
            ET.SubElement(mem_desc, "dc:title").text = title

        # ✅ link memory → CHO
        ET.SubElement(mem_desc, "edm:isRelatedTo").set(
            "rdf:resource",
            f"http://example.org/cho/{cho_id}"
        )

    # -----------------------------
    # Output
    # -----------------------------
    _indent(root)
    rdf_string = ET.tostring(root, encoding="unicode")

    _save_file(rdf_string, f"cho_{cho_id}_all.rdf")
    return rdf_string


# =========================================================
# MEMORY EXPORT (MULTIPLE CHOs SUPPORTED)
# =========================================================

def export_memory_rdf(memory):
    if not memory:
        messagebox.showerror("Error", "No memory selected")
        return ""

    memory_id = _get_id(memory)

    root = _create_root()

    desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/memory/{memory_id}"
    })

    ET.SubElement(desc, "rdf:type").text = "edm:WebResource"
    ET.SubElement(desc, "dc:identifier").text = memory_id

    title = _safe_text(memory.title)
    if title:
        ET.SubElement(desc, "dc:title").text = title

    metadata = extract_metadata(memory.text or "")

    cho_refs = set()

    # -----------------------------
    # Memory intrinsic metadata
    # -----------------------------
    for md in metadata:
        if md.get("type") == MetadataType.MEMORY.value:
            field = md.get("field")
            value = _safe_text(md.get("value"))

            if field and value:
                ET.SubElement(desc, field).text = value

    # -----------------------------
    # CHO links
    # -----------------------------
    for md in metadata:
        if md.get("type") == MetadataType.CHO.value:
            if md.get("cho"):
                cho_refs.add(md.get("cho"))

    for cho_id in cho_refs:
        ET.SubElement(desc, "edm:isRelatedTo").set(
            "rdf:resource",
            f"http://example.org/cho/{cho_id}"
        )

    # -----------------------------
    # Output
    # -----------------------------
    _indent(root)
    rdf_string = ET.tostring(root, encoding="unicode")

    _save_file(rdf_string, f"memory_{memory_id}.rdf")
    return rdf_string