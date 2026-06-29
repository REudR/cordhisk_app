import re
import html
from services.metadata import (
    extract_metadata,
    parse_text_and_spans,
    rebuild_text_from_spans
)
from services.types import MetadataType


# =========================
# CLEAN TEXT
# =========================
def clean_text(text):
    if not text:
        return ""

    text = html.unescape(text)
    text = text.replace("\r\n", "\n").strip()

    # remove RDF
    text = re.sub(r'<rdf:RDF.*?</rdf:RDF>', '', text, flags=re.DOTALL)

    return text


# =========================
# REMOVE MEMORY BLOCK
# =========================
def remove_memory_block(text):
    return re.sub(
        r'===\s*MEMORY METADATA START\s*===.*?===\s*MEMORY METADATA END\s*===',
        '',
        text,
        flags=re.DOTALL
    )


# =========================
# BUILD MEMORY BLOCK ✅ (centralized)
# =========================
def build_memory_block(metadata):
    lines = [
        f'<{k} type="memory">{v}</{k}>'
        for k, v in metadata.items()
        if v.strip()
    ]

    return (
        "=== MEMORY METADATA START ===\n"
        + "\n".join(lines)
        + "\n=== MEMORY METADATA END ===\n\n"
    )


# =========================
# BUILD SPANS FROM METADATA
# =========================
def build_spans(clean_text, memory_md, cho_md):
    spans = []

    # CHO
    for md in cho_md:
        start = clean_text.find(md["value"])
        if start == -1:
            continue

        spans.append({
            "start": start,
            "end": start + len(md["value"]),
            "field": md["field"],
            "value": md["value"],
            "cho": md.get("cho"),
            "type": MetadataType.CHO.value
        })

    # MEMORY
    for field, value in memory_md.items():
        start = clean_text.find(value)

        if start == -1:
            spans.append({
                "field": field,
                "value": value,
                "type": MetadataType.MEMORY.value
            })
            continue

        spans.append({
            "start": start,
            "end": start + len(value),
            "field": field,
            "value": value,
            "type": MetadataType.MEMORY.value
        })

    return spans

# =========================
# FULL REBUILD PIPELINE ✅
# =========================
def rebuild_memory_text(original_text, new_metadata):

    txt = clean_text(original_text)

    # remove existing memory block
    txt = remove_memory_block(txt)

    # parse clean content
    clean, _ = parse_text_and_spans(txt)

    # preserve CHO metadata
    cho_md = [
        md for md in extract_metadata(original_text)
        if md.get("type") == MetadataType.CHO.value
    ]

    # rebuild spans
    spans = build_spans(clean, new_metadata, cho_md)

    # rebuild block
    block = build_memory_block(new_metadata)

    # rebuild text
    content = rebuild_text_from_spans(clean, spans).lstrip("\n")

    return block + content

def rebuild_from_spans(clean_text, spans):
    from collections import OrderedDict

    # ✅ Rebuild inline tags
    content = rebuild_text_from_spans(clean_text, spans)

    # ✅ Extract MEMORY metadata from spans
    metadata = OrderedDict()
    for s in spans:
        if s.get("type") == MetadataType.MEMORY.value:
            field = s.get("field")
            value = s.get("value")

            if field and value:
                metadata[field] = value  # automatic dedup

    # ✅ Build block
    block = build_memory_block(metadata)

    # ✅ Final result
    return block + content.lstrip("\n"), metadata
