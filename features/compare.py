from db import session, Memory
from services.metadata import extract_metadata
from utils import make_tree_window, MetadataType

def compare(cho_id):
    tree = make_tree_window("Compare", ("Memory", "Field", "Value"))

    for m in session.query(Memory):
        for md in extract_metadata(m.text):
            if md.get("type") == MetadataType.CHO.value and md.get("cho") == cho_id:
                tree.insert("", "end",
                    values=(m.custom_id, md["field"], md["value"]))
