import re
import xml.etree.ElementTree as ET
from services.types import MetadataType


# =========================
# REGEX (REAL TAGS)
# =========================
COMBINED_RE = re.compile(
    r'<(?P<field>[a-zA-Z0-9:_-]+)'
    r'(?:\s+cho="(?P<cho>[^"]+)"|\s+type="(?P<type>memory)")>'
    r'(?P<value>.*?)</\1>',
    re.DOTALL
)


# =========================
# BUILD RDF BLOCK
# =========================
def build_rdf_block(metadata):
    if not metadata:
        return ""

    root = ET.Element("rdf:RDF")
    desc = ET.SubElement(root, "rdf:Description")

    for field, value in metadata.items():
        tag = field.replace(":", "_")
        ET.SubElement(desc, tag).text = value

    return ET.tostring(root, encoding="unicode") + "\n\n"


# =========================
# PARSE TEXT + SPANS ✅ CLEAN
# =========================
def parse_text_and_spans(text):
    if not text:
        return "", []

    try:
        # =========================
        # STEP 1: Extract memory metadata block
        # =========================
        block_pattern = r'===\s*MEMORY METADATA START\s*===(.*?)===\s*MEMORY METADATA END\s*==='
        block_match = re.search(block_pattern, text, re.DOTALL)

        memory_md = []

        if block_match:
            block = block_match.group(1)

            for m in COMBINED_RE.finditer(block):
                if m.group("type") == "memory":
                    memory_md.append({
                        "field": m.group("field"),
                        "value": m.group("value"),
                        "type": MetadataType.MEMORY.value
                    })

            # remove block from visible text
            text = re.sub(block_pattern, '', text, flags=re.DOTALL)

        # =========================
        # STEP 2: Parse inline tags
        # =========================
        spans = []
        clean = ""
        idx = 0

        for m in COMBINED_RE.finditer(text):
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
                "type": MetadataType.MEMORY.value
                    if m.group("type") == "memory"
                    else MetadataType.CHO.value
            })

            idx = end

        clean += text[idx:]

        # =========================
        # STEP 3: Map memory metadata into clean text
        # =========================
        for md in memory_md:
            value = md["value"]
            start = clean.find(value)

            span = {
                "field": md["field"],
                "value": value,
                "type": MetadataType.MEMORY.value
            }

            if start != -1:
                span["start"] = start
                span["end"] = start + len(value)

            spans.append(span)

        spans.sort(key=lambda s: s.get("start", -1))

        return clean, spans

    except Exception as e:
        print("ERROR in parse_text_and_spans:", e)
        return "", []


# =========================
# EXTRACT METADATA ✅ CLEAN
# =========================
def extract_metadata(text):
    if not text:
        return []

    metadata = []

    # =========================
    # MEMORY BLOCK
    # =========================
    memory_blocks = re.findall(
        r'=== MEMORY METADATA START ===(.*?)=== MEMORY METADATA END ===',
        text,
        flags=re.DOTALL
    )

    for block in memory_blocks:
        for m in COMBINED_RE.finditer(block):
            metadata.append({
                "field": m.group("field"),
                "cho": None,
                "value": m.group("value"),
                "type": MetadataType.MEMORY.value
            })

    # =========================
    # REMOVE MEMORY BLOCK
    # =========================
    text_wo_memory = re.sub(
        r'=== MEMORY METADATA START ===.*?=== MEMORY METADATA END ===',
        '',
        text,
        flags=re.DOTALL
    )

    # =========================
    # CHO METADATA
    # =========================
    for m in COMBINED_RE.finditer(text_wo_memory):
        metadata.append({
            "field": m.group("field"),
            "cho": m.group("cho"),
            "value": m.group("value"),
            "type": MetadataType.CHO.value
        })

    return metadata


# =========================
# MEMORY TITLE
# =========================
def get_memory_title(text, fallback):
    if not text:
        return fallback

    text = text.lstrip("\ufeff \n\t")

    match = re.search(
        r'<(?:web:)?dc:title[^>]*type="memory"[^>]*>(.*?)</(?:web:)?dc:title>',
        text,
        re.DOTALL
    )
    if match:
        return match.group(1).strip()

    match = re.search(
        r'<(?:web:)?dc:title[^>]*>(.*?)</(?:web:)?dc:title>',
        text,
        re.DOTALL
    )
    if match:
        return match.group(1).strip()

    return fallback


# =========================
# REBUILD TEXT FROM SPANS
# =========================
def rebuild_text_from_spans(text, spans):
    offset = 0

    valid_spans = [s for s in spans if "start" in s and "end" in s]

    for span in sorted(valid_spans, key=lambda s: s["start"]):
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