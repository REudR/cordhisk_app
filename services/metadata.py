import re
import xml.etree.ElementTree as ET
from utils import RE_METADATA, RE_MEMORY_METADATA, MetadataType

TAG_RE = re.compile(
    r'<(?P<field>[a-zA-Z0-9:_-]+)\s+cho="(?P<cho>[^"]+)">(?P<value>.*?)</\1>',
    re.DOTALL
)

MEMORY_TAG_RE = re.compile(
    r'<(?P<field>[a-zA-Z0-9:_-]+)\s+type="memory">(?P<value>.*?)</\1>',
    re.DOTALL
)

def parse_text_and_spans(text):
    """Parse both CHO-linked and Memory-intrinsic metadata from text"""
    spans = []
    clean = ""
    idx = 0

    # Parse CHO-linked metadata
    for m in TAG_RE.finditer(text):
        start, end = m.span()
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
            "type": MetadataType.CHO.value
        })
        idx = end

    # Parse memory-intrinsic metadata
    remaining = text[idx:]
    idx2 = 0
    for m in MEMORY_TAG_RE.finditer(remaining):
        start, end = m.span()
        clean += remaining[idx2:start]
        inner = m.group("value")
        span_start = len(clean)
        clean += inner
        span_end = len(clean)

        spans.append({
            "start": span_start,
            "end": span_end,
            "field": m.group("field"),
            "value": inner,
            "type": MetadataType.MEMORY.value
        })
        idx2 = end

    clean += remaining[idx2:]
    spans.sort(key=lambda s: s["start"])

    return clean, spans

def extract_metadata(text):
    """Extract all metadata (CHO-linked and memory-intrinsic)"""
    metadata = []
    
    # CHO-linked metadata
    for m in TAG_RE.finditer(text or ""):
        metadata.append({
            "field": m.group("field"),
            "cho": m.group("cho"),
            "value": m.group("value"),
            "type": MetadataType.CHO.value
        })
    
    # Memory-intrinsic metadata
    for m in MEMORY_TAG_RE.finditer(text or ""):
        metadata.append({
            "field": m.group("field"),
            "value": m.group("value"),
            "type": MetadataType.MEMORY.value
        })
    
    return metadata

def get_memory_title(text, fallback):
    """Extract memory title from metadata tags"""
    # Try memory-intrinsic title first
    match = re.search(r'<web:dc:title type="memory">(.*?)</web:dc:title>', text or "")
    if match:
        return match.group(1)
    
    # Fallback to original format
    match = re.search(r"<dc[:_]title>(.*?)</dc[:_]title>", text or "")
    return match.group(1) if match else fallback

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

def rebuild_text_from_spans(text, spans):
    """Rebuild text with metadata tags from spans"""
    offset = 0

    for span in sorted(spans, key=lambda s: s["start"]):
        start = span["start"] + offset
        end = span["end"] + offset

        if span.get("type") == MetadataType.CHO.value:
            # CHO-linked metadata with cho attribute
            wrapped = f'<{span["field"]} cho="{span["cho"]}">{text[start:end]}</{span["field"]}>'
        else:
            # Memory-intrinsic metadata with type attribute
            wrapped = f'<{span["field"]} type="memory">{text[start:end]}</{span["field"]}>'

        text = text[:start] + wrapped + text[end:]
        offset += len(wrapped) - (end - start)

    return text
