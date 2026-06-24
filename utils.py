import re
import tkinter as tk
from tkinter import ttk
from enum import Enum

RE_METADATA = re.compile(r'<(.*?) cho="(.*?)">(.*?)</\1>')
RE_MEMORY_METADATA = re.compile(r'<(.*?) type="memory">(.*?)</\1>')
RE_ANY_TAG = re.compile(r"<.*?>(.*?)</.*?>")
RE_STRIP = re.compile(r"</?[^>]+>")

class MetadataType(Enum):
    """Distinguishes metadata origins"""
    MEMORY = "memory"      # WebResource fields - intrinsic to the memory
    CHO = "cho"            # CHO/Agent fields - linked to Cultural Heritage Objects

# Field definitions by type and category
METADATA_FIELDS = {
    "CHO": {
        "type": MetadataType.CHO,
        "fields": [
            "dc:contributor", "dc:coverage", "dc:creator", "dc:date",
            "dc:description", "dc:format", "dc:language", "dc:publisher",
            "dc:source", "dc:subject", "dc:title", "dc:type",
            "dcterms:created", "dcterms:extent", "dcterms:issued",
            "dcterms:medium", "dcterms:provenance", "dcterms:spatial",
            "dcterms:tableOfContents", "dcterms:temporal"
        ]
    },
    "Agent": {
        "type": MetadataType.CHO,
        "fields": [
            "oaf:name", "rdaGr2:biographicalInformation",
            "rdaGr2:dateOfBirth", "rdaGr2:dateOfDeath",
            "rdaGr2:dateOfEstablishment", "rdaGr2:dateOfTermination",
            "rdaGr2:gender", "rdaGr2:placeOfBirth",
            "rdaGr2:placeOfDeath", "rdaGr2:professionOrOccupation"
        ]
    },
    "WebResource": {
        "type": MetadataType.MEMORY,
        "fields": [
            "web:dc:creator", "web:dc:description",
            "web:dc:source", "web:dcterms:created"
        ]
    }
}

def field_to_alias(field):
    """Convert metadata field to user-friendly label"""

    if not field:
        return ""

    # Remove namespace
    name = field.split(":")[-1]

    # Split camelCase
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)

    # Replace underscores
    name = name.replace("_", " ")

    return name.capitalize()


def field_to_display(field):
    """Convert field to '[Category] Alias' format"""

    category = get_category_for_field(field) or "Unknown"
    alias = field_to_alias(field)

    return f"[{category}] {alias}"


def display_to_field(display, fields):
    """Convert display string back to real field"""

    for f in fields:
        if field_to_display(f) == display:
            return f

    return None

def alias_to_field(alias, fields):
    """Find the real field corresponding to an alias"""

    for f in fields:
        if field_to_alias(f) == alias:
            return f

    return None

def get_all_fields_by_type(metadata_type):
    """Return all fields for a given metadata type (MEMORY or CHO)"""
    fields = []
    for config in METADATA_FIELDS.values():
        # ✅ FIX: compare values instead of enum objects
        if config["type"].value == metadata_type.value:
            fields.extend(config["fields"])
    return fields

def get_category_for_field(field):
    """Return the category (CHO, Agent, WebResource) for a field"""
    for category, config in METADATA_FIELDS.items():
        if field in config["fields"]:
            return category
    return None

def get_metadata_type_for_field(field):
    """Return the MetadataType for a field"""
    for category, config in METADATA_FIELDS.items():
        if field in config["fields"]:
            return config["type"]
    return None

def load_list(listbox, items, fmt):
    listbox.delete(0, tk.END)
    for item in items:
        listbox.insert(tk.END, fmt(item))

def make_tree_window(title, columns=None):
    win = tk.Toplevel()
    win.title(title)

    frame = tk.Frame(win)
    frame.pack(fill="both", expand=True)

    if columns:
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
    else:
        tree = ttk.Treeview(frame)

    scroll = ttk.Scrollbar(frame, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)

    scroll.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    return tree

def field_to_alias(field):
    """Convert metadata field to user-friendly label"""
    if not field:
        return ""

    name = field.split(":")[-1]
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = name.replace("_", " ")

    return name.capitalize()


def field_to_display(field):
    """Convert field to '[Category] Alias' format"""
    category = get_category_for_field(field) or "Unknown"
    alias = field_to_alias(field)
    return f"[{category}] {alias}"


def display_to_field(display, fields):
    """Convert display string back to real field"""
    for f in fields:
        if field_to_display(f) == display:
            return f
    return None
