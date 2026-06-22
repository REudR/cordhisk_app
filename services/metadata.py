import re
import xml.etree.ElementTree as ET
from utils import RE_METADATA
import re

TAG_RE = re.compile(
    r'<(?P<field>[a-zA-Z0-9:_-]+)\s+cho="(?P<cho>[^"]+)">(?P<value>.*?)</\1>',
    re.DOTALL
)

def parse_text_and_spans(text):
    spans = []
    clean = ""
    idx = 0

    for m in TAG_RE.finditer(text):
        start, end = m.span()

        # text before tag
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
            "value": inner
        })

        idx = end

    # remaining text
    clean += text[idx:]

    return clean, spans

def extract_metadata(text):
    return [
        {"field": f, "cho": c, "value": v}
        for f, c, v in RE_METADATA.findall(text or "")
    ]

def get_memory_title(text, fallback):
    match = re.search(r"<dc[:_]title>(.*?)</dc[:_]title>", text or "")
    return match.group(1) if match else fallback

def build_rdf_block(metadata):
    if not metadata:
        return ""

    root = ET.Element("rdf:RDF")
    desc = ET.SubElement(root, "rdf:Description")

    for field, value in metadata.items():
        tag = field.replace(":", "_")
        ET.SubElement(desc, tag).text = value

    return ET.tostring(root, encoding="unicode") + "\n\n"

def rebuild_text_from_spans(text, spans):
    offset = 0

    for span in sorted(spans, key=lambda s: s["start"]):
        start = span["start"] + offset
        end   = span["end"] + offset

        wrapped = f'<{span["field"]} cho="{span["cho"]}">{text[start:end]}</{span["field"]}>'

        text = text[:start] + wrapped + text[end:]

        offset += len(wrapped) - (end - start)

    return text