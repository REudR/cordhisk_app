import re
from utils import MetadataType
import xml.etree.ElementTree as ET

# ✅ ONE unified regex (CHO + memory metadata)
COMBINED_RE = re.compile(
    r'<(?P<field>[a-zA-Z0-9:_-]+)'
    r'(?:\s+cho="(?P<cho>[^"]+)"|\s+type="(?P<type>memory)")>'
    r'(?P<value>.*?)</\1>',
    re.DOTALL
)

def build_rdf_block(metadata):
    """Build RDF block from metadata dict"""
    if not metadata:
        return ""

    root = ET.Element("rdf:RDF")
    desc = ET.SubElement(root, "rdf:Description")

    for field, value in metadata.items():
        tag = field.replace(":", "_")
        ET.SubElement(desc, tag).text = value

    return ET.tostring(root, encoding="unicode") + "\n\n"
    
# =========================
# PARSE TEXT + SPANS
# =========================
def parse_text_and_spans(text):
    spans = []
    clean = ""
    idx = 0

    for m in COMBINED_RE.finditer(text or ""):
        start, end = m.span()

        # Append normal text
        clean += text[idx:start]

        inner = m.group("value")

        span_start = len(clean)
        clean += inner
        span_end = len(clean)

        spans.append({
            "start": span_start,
            "end": span_end,
            "field": m.group("field"),
            "cho": m.group("cho"),
            "value": inner,
            "type": MetadataType.MEMORY.value
                    if m.group("type") == "memory"
                    else MetadataType.CHO.value
        })

        idx = end

    clean += text[idx:]

    return clean, spans


# =========================
# EXTRACT METADATA
# =========================
def extract_metadata(text):
    metadata = []

    for m in COMBINED_RE.finditer(text or ""):
        metadata.append({
            "field": m.group("field"),
            "cho": m.group("cho"),
            "value": m.group("value"),
            "type": MetadataType.MEMORY.value
                    if m.group("type") == "memory"
                    else MetadataType.CHO.value
        })

    return metadata


# =========================
# MEMORY TITLE
# =========================
def get_memory_title(text, fallback):
    match = re.search(
        r'<web:dc:title type="memory">(.*?)</web:dc:title>',
        text or ""
    )
    if match:
        return match.group(1)

    match = re.search(
        r'<dc[:_]title>(.*?)</dc[:_]title>',
        text or ""
    )

    return match.group(1) if match else fallback


# =========================
# REBUILD TEXT
# =========================
def rebuild_text_from_spans(text, spans):
    offset = 0

    for span in sorted(spans, key=lambda s: s["start"]):
        start = span["start"] + offset
        end = span["end"] + offset

        if span["type"] == MetadataType.MEMORY.value:
            wrapped = (
                f'<{span["field"]} type="memory">'
                f'{text[start:end]}'
                f'</{span["field"]}>'
            )
        else:
            wrapped = (
                f'<{span["field"]} cho="{span["cho"]}">'
                f'{text[start:end]}'
                f'</{span["field"]}>'
            )

        text = text[:start] + wrapped + text[end:]
        offset += len(wrapped) - (end - start)

    return text