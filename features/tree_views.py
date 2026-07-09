from utils import make_tree_window
from db import session, Memory
from services.metadata import extract_metadata

def show_cho_tree(cid):
    tree = make_tree_window(f"CHO {cid}")
    root = tree.insert("", "end", text=f"CHO {cid}")

    for m in session.query(Memory):
        meta = [x for x in extract_metadata(m.text) if x["cho"] == cid]

        if meta:
            mem_node = tree.insert(root, "end", text=m.custom_id)
            for md in meta:
                tree.insert(mem_node, "end",
                            text=f"{md['field']} → {md['value']}")

def show_memory_tree(mem):
    tree = make_tree_window(f"Memory {mem.custom_id}")
    root = tree.insert("", "end", text=mem.custom_id)

    grouped = {}
    for md in extract_metadata(mem.text):
        grouped.setdefault(md["cho"], []).append(md)

    for cid, items in grouped.items():
        node = tree.insert(root, "end", text=f"CHO {cid}")
        for md in items:
            tree.insert(node, "end",
                        text=f"{md['field']} → {md['value']}")
