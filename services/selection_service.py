from services.metadata import extract_metadata
from services.types import MetadataType
from db import session, Memory


# =========================
# CHO → MEMORY LINKS
# =========================
def compute_links_for_cho(cid):
    linked_memories = set()

    for m in session.query(Memory):
        for md in extract_metadata(m.text):
            if md.get("type") == MetadataType.CHO.value and md.get("cho") == cid:
                linked_memories.add(m.custom_id)

    return linked_memories


# =========================
# MEMORY → CHO LINKS
# =========================
def compute_links_for_memory(memory):
    cho_ids = set()

    for md in extract_metadata(memory.text):
        if md.get("type") == MetadataType.CHO.value:
            if md.get("cho"):
                cho_ids.add(md.get("cho"))

    return cho_ids