import html
import os
import re
import tempfile
import uuid
import xml.etree.ElementTree as ET

from flask import Flask, Response, redirect, render_template_string, request, url_for
from sqlalchemy import func

from config import APP_DATA_DIR
from db import CHO, Memory, session
from services.memory_service import rebuild_memory_text
from services.metadata import extract_metadata, get_memory_title, parse_text_and_spans
from services.metadata_schema import METADATA_FIELDS
from services.web_templates import COMPARE_TEMPLATE, HTML_TEMPLATE, IMPORT_TEMPLATE, SEARCH_TEMPLATE
from services.types import MetadataType


CHO_FIELDS = [
    {"field": field, "label": meta.get("label", field)}
    for category in ("CHO", "Agent")
    for field, meta in METADATA_FIELDS.get(category, {}).get("fields", {}).items()
]

SEARCH_PAGE_SIZE = 10
IMPORT_FIELDS = ("dc:title", "dc:creator", "dc:date", "dc:subject", "dc:description")
MEMORY_LICENSE_FIELD = "dc:license"
MEMORY_LICENSE_OPTIONS = (
  "CC BY",
  "CC BY-SA",
  "CC BY-SA 3.0 IGO",
  "CC BY-ND",
  "CC BY-NC",
  "CC BY-NC-SA",
  "CC BY-NC-ND",
  "Restricted",
)

MEMORY_FIELDS = [
    {"field": field, "label": field.split(":")[-1].replace("_", " ").title()}
    for field in IMPORT_FIELDS
]


def _metadata_label(field_name):
  if not field_name:
    return "Metadata"
  for group in METADATA_FIELDS.values():
    label = group.get("fields", {}).get(field_name, {}).get("label")
    if label:
      return label
  return field_name.split(":")[-1].replace("_", " ").replace("-", " ").title()


def _metadata_description(field_name):
  if not field_name:
    return ""
  for group in METADATA_FIELDS.values():
    description = group.get("fields", {}).get(field_name, {}).get("description")
    if description:
      return description
  return _metadata_label(field_name)


def _normalize_text(text):
  text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
  text = re.sub(r"[ \t]+", " ", text)
  text = re.sub(r"\n[ \t]*", "\n", text)
  text = re.sub(r"\n{3,}", "\n\n", text)
  return text

def _extract_memory_block_metadata(text):
    from services.metadata import COMBINED_RE

    pattern = r'===\s*MEMORY METADATA START\s*===(.*?)===\s*MEMORY METADATA END\s*==='
    match = re.search(pattern, text or "", re.DOTALL)
    metadata = {}

    if match:
        block = match.group(1)
        for m in COMBINED_RE.finditer(block):
            if m.group("type") == "memory":
                metadata[m.group("field")] = m.group("value")

    return metadata

def _memory_txt_path(mid):
    safe_mid = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(mid or "")).strip("_")
    if not safe_mid:
        safe_mid = str(uuid.uuid4())[:8]
    return os.path.join(APP_DATA_DIR, f"{safe_mid}.txt")


def _write_memory_text_file(mid, text):
    path = _memory_txt_path(mid)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text or "")
    return path


def _persist_memory_to_disk(memory, text=None):
    if text is not None:
        memory.text = text
    memory.file_path = _write_memory_text_file(memory.custom_id or memory.id, memory.text or "")
    return memory.file_path


def _find_nth_occurrence(text, term, occurrence_index):
  if not text or not term:
    return -1
  target_index = max(0, int(occurrence_index or 0))
  search_from = 0
  found_count = 0
  step = max(len(term), 1)
  while True:
    pos = text.find(term, search_from)
    if pos == -1:
      return -1
    if found_count == target_index:
      return pos
    found_count += 1
    search_from = pos + step


def _visible_span_to_raw_span(raw_text, visible_start, visible_end):
  if raw_text is None:
    return None
  if visible_start < 0 or visible_end < visible_start:
    return None

  hidden_blocks = []
  block_pattern = r'===\s*MEMORY METADATA START\s*===.*?===\s*MEMORY METADATA END\s*==='
  for match in re.finditer(block_pattern, raw_text, re.DOTALL):
    hidden_blocks.append((match.start(), match.end()))

  raw_start = None
  raw_end = None
  visible_pos = 0
  i = 0
  text_len = len(raw_text)
  hidden_idx = 0

  while i < text_len:
    if hidden_idx < len(hidden_blocks):
      hidden_start, hidden_end = hidden_blocks[hidden_idx]
      if i >= hidden_end:
        hidden_idx += 1
        continue
      if i >= hidden_start:
        i = hidden_end
        hidden_idx += 1
        continue

    ch = raw_text[i]
    if ch == "<":
      tag_end = raw_text.find(">", i + 1)
      if tag_end != -1:
        i = tag_end + 1
        continue

    if raw_start is None and visible_pos == visible_start:
      raw_start = i
    if raw_end is None and visible_pos == visible_end:
      raw_end = i
      break

    visible_pos += 1
    i += 1

  if raw_start is None and visible_pos == visible_start:
    raw_start = text_len
  if raw_end is None and visible_pos == visible_end:
    raw_end = text_len

  if raw_start is None or raw_end is None:
    return None
  return raw_start, raw_end


def _build_paragraphs(text):
    clean_text, spans = parse_text_and_spans(text or "")
    if not clean_text:
        return []

    paragraphs = []
    paragraph_bounds = []
    start = 0
    for match in re.finditer(r"\n\s*\n", clean_text):
        paragraph_bounds.append((start, match.start()))
        start = match.end()
    paragraph_bounds.append((start, len(clean_text)))

    cho_tag_index = 0
    for para_start, para_end in paragraph_bounds:
        para_text = clean_text[para_start:para_end].strip()
        if not para_text:
            continue

        parts = []
        cursor = para_start
        for span in sorted(spans, key=lambda item: item.get("start", -1)):
            span_start = span.get("start", -1)
            span_end = span.get("end", -1)
            if span_start < 0 or span_end < 0:
                continue
            if span_start < para_end and span_end > para_start:
                if span_start > cursor:
                    text_segment = clean_text[cursor:span_start]
                    if text_segment:
                        normalized_segment = _normalize_text(text_segment)
                        if normalized_segment:
                            parts.append({"type": "text", "value": normalized_segment})
                highlighted_value = _normalize_text(clean_text[span_start:span_end])
                if highlighted_value:
                    is_cho_tag = span.get("type") == MetadataType.CHO.value
                    parts.append({
                        "type": "span",
                        "value": highlighted_value,
                        "kind": "cho" if is_cho_tag else "memory",
                        "field": span.get("field", ""),
                        "cho_tag_index": cho_tag_index if is_cho_tag else None,
                    })
                    if is_cho_tag:
                        cho_tag_index += 1
                cursor = max(cursor, span_end)
        if cursor < para_end:
            tail = clean_text[cursor:para_end]
            if tail:
                normalized_tail = _normalize_text(tail)
                if normalized_tail:
                    parts.append({"type": "text", "value": normalized_tail})
        if parts:
            paragraphs.append(parts)

    if not paragraphs:
        return [{"type": "text", "value": _normalize_text(clean_text)}]

    return paragraphs


def _remove_nth_cho_tag(text, target_index):
  if not text:
    return text
  try:
    target_index = max(0, int(target_index))
  except (TypeError, ValueError):
    return text

  pattern = re.compile(r'<(?P<field>[a-zA-Z0-9:_-]+)\s+cho="(?P<cho>[^"]+)">(?P<value>.*?)</(?P=field)>', re.DOTALL)
  current_index = 0
  for match in pattern.finditer(text):
    if current_index == target_index:
      return text[:match.start()] + match.group("value") + text[match.end():]
    current_index += 1
  return text


def _load_context(memory_id=None, focus_cho=None):
    memories = session.query(Memory).order_by(func.lower(Memory.custom_id), Memory.id).all()
    chos = session.query(CHO).order_by(func.lower(CHO.custom_id), CHO.id).all()
    cho_lookup = _build_cho_lookup(chos)

    selected_memory = None
    metadata = []
    paragraphs = []
    memory_metadata_items = []
    cho_metadata_items = []

    if memory_id is not None:
      selected_memory = session.get(Memory, memory_id)
    elif memories:
        selected_memory = memories[0]

    if selected_memory is not None:
        metadata = extract_metadata(selected_memory.text or "")
        if not selected_memory.title:
            selected_memory.title = get_memory_title(selected_memory.text or "", "Untitled memory")

        memory_metadata_items = [
            {"field": md["field"], "value": md["value"]}
            for md in metadata
          if md.get("type") == MetadataType.MEMORY.value and md.get("field") not in {"dc:identifier", MEMORY_LICENSE_FIELD}
        ]
        cho_metadata_items = [
          {
            "index": index,
            "cho": md.get("cho"),
            "label": _cho_display_label(cho_lookup.get(str(md.get("cho")))) or str(md.get("cho")),
            "field": md["field"],
            "value": md["value"],
          }
          for index, md in enumerate(
            md for md in metadata
            if md.get("type") == MetadataType.CHO.value and md.get("cho")
          )
        ]
        paragraphs = _build_paragraphs(selected_memory.text or "")

    return memories, chos, selected_memory, metadata, paragraphs, memory_metadata_items, cho_metadata_items, focus_cho


def _memory_metadata_dict(text):
    metadata = {}
    for md in extract_metadata(text or ""):
        if md.get("type") == MetadataType.MEMORY.value:
            field = md.get("field")
            value = md.get("value")
            if field and value is not None:
                metadata[field] = value
    return metadata


def _memory_license_value(memory):
  value = getattr(memory, "license", None)
  return value.strip() if isinstance(value, str) else (value or "")


def _build_metadata_cache(memories):
  return {memory.id: extract_metadata(memory.text or "") for memory in memories}


def _build_cho_lookup(cho_rows):
  lookup = {}
  for cho in cho_rows:
    if cho.id is not None:
      lookup[str(cho.id)] = cho
    if cho.custom_id:
      lookup[str(cho.custom_id)] = cho
  return lookup


def _cho_display_label(cho):
  if cho is None:
    return ""
  cho_id = str(cho.custom_id or cho.id)
  return f"{cho_id} ({cho.title})" if cho.title else cho_id


def _build_graph_data(selected_memory_id=None, focus_cho=None):
  memories = session.query(Memory).order_by(Memory.id).all()
  cho_rows = session.query(CHO).order_by(CHO.id).all()
  metadata_by_memory_id = _build_metadata_cache(memories)
  cho_lookup = _build_cho_lookup(cho_rows)
  nodes = []
  edges = []
  edge_ids = set()
  seen_nodes = {}
  cho_metadata_positions = {}
  cho_base_y = {}

  def add_node(node_id, label, group, x, y, link, radius=32, parent_id="", details="", memory_owner_id=""):
    if node_id not in seen_nodes:
      seen_nodes[node_id] = {
        "id": node_id,
        "label": label,
        "group": group,
        "x": x,
        "y": y,
        "link": link,
        "radius": radius,
        "parent_id": parent_id,
        "details": details,
        "memory_owner_id": memory_owner_id,
      }
      nodes.append(seen_nodes[node_id])
    elif memory_owner_id:
      existing = seen_nodes[node_id].get("memory_owner_id", "")
      owner_ids = [item for item in existing.split(",") if item]
      if memory_owner_id not in owner_ids:
        owner_ids.append(memory_owner_id)
        seen_nodes[node_id]["memory_owner_id"] = ",".join(owner_ids)
    return seen_nodes[node_id]

  def add_edge(from_node, to_node):
    key = (from_node["id"], to_node["id"])
    if key in edge_ids:
      return
    edge_ids.add(key)
    edges.append((from_node, to_node))

  def matches_cho(metadata_items, cho_id):
    for md in metadata_items:
      if md.get("type") == MetadataType.CHO.value and str(md.get("cho")) == str(cho_id):
        return True
    return False

  if focus_cho:
    target_cho = next((item for item in cho_rows if str(item.custom_id) == str(focus_cho) or str(item.id) == str(focus_cho)), None)
    if target_cho is None:
      target_cho = next((item for item in cho_rows if str(item.custom_id) == str(focus_cho)), None)
    relevant_memories = []
    for memory in memories:
      metadata_items = metadata_by_memory_id.get(memory.id, [])
      if matches_cho(metadata_items, focus_cho):
        relevant_memories.append(memory)
    memories = relevant_memories
    cho_rows = [target_cho] if target_cho is not None else []
  elif selected_memory_id is not None:
    selected_memory = session.get(Memory, selected_memory_id)
    memories = [selected_memory] if selected_memory is not None else []
    cho_rows = []
    if selected_memory is not None:
      for md in metadata_by_memory_id.get(selected_memory.id, []):
        if md.get("type") == MetadataType.CHO.value and md.get("cho"):
          cho = cho_lookup.get(str(md.get("cho")))
          if cho is not None:
            cho_rows.append(cho)
    cho_rows = list(dict.fromkeys(cho_rows))

  if cho_rows:
    row_gap = 70
    cursor_y = 140
    for cho in cho_rows:
      cho_key = str(cho.custom_id or cho.id)
      cho_refs = {str(cho.id), cho_key}
      unique_rows = set()
      for memory in memories:
        for md in metadata_by_memory_id.get(memory.id, []):
          if md.get("type") != MetadataType.CHO.value:
            continue
          if str(md.get("cho")) not in cho_refs:
            continue
          unique_rows.add((md.get("field") or "metadata", str(md.get("value", ""))))
      cho_base_y[cho_key] = cursor_y
      band_height = max(220, 90 + len(unique_rows) * row_gap)
      cursor_y += band_height

  for index, memory in enumerate(memories):
    memory_link = f"/?memory_id={memory.id}" if memory.id else "/"
    memory_node = add_node(
      f"memory:{memory.id}",
      memory.title or f"Memory {memory.id}",
      "memory",
      180,
      140 + index * 180,
      memory_link,
      36,
      "",
      memory.custom_id or str(memory.id),
    )

    metadata_items = metadata_by_memory_id.get(memory.id, [])
    for md_index, md in enumerate(metadata_items):
      if md.get("type") == MetadataType.MEMORY.value:
        continue  # skip memory metadata entirely
      elif md.get("type") == MetadataType.CHO.value and md.get("cho"):
        cho = cho_lookup.get(str(md.get("cho")))
        if cho is None:
          continue
        cho_key = str(cho.custom_id or cho.id)
        cho_y = cho_base_y.get(cho_key, 140)
        cho_link = f"/?memory_id={selected_memory_id or ''}&focus_cho={cho.custom_id or cho.id}" if selected_memory_id is not None else f"/?focus_cho={cho.custom_id or cho.id}"
        field_name = md.get("field", "")
        display_field = _metadata_label(field_name)
        cho_label = _cho_display_label(cho)
        cho_node = add_node(
          f"cho:{cho.custom_id or cho.id}",
          cho_label,
          "cho",
          760,
          cho_y,
          cho_link,
          36,
          "",
          f"{cho_label}: {display_field} = {md.get('value', '')}",
        )
        metadata_label = display_field
        position_key = (cho_key, field_name or "metadata", str(md.get("value", "")))
        cho_column_positions = cho_metadata_positions.setdefault(cho_key, {})
        metadata_row = cho_column_positions.setdefault(position_key, len(cho_column_positions))
        metadata_node = add_node(
          f"cho_md:{cho_key}:{metadata_row}",
          metadata_label,
          "cho_metadata",
          600,
          cho_y + metadata_row * 70,
          cho_link,
          24,
          f"cho:{cho.custom_id or cho.id}",
          f"{metadata_label}: {md.get('value', '')}",
          f"memory:{memory.id}",
        )
        add_edge(memory_node, metadata_node)
        add_edge(metadata_node, cho_node)

  return nodes, edges


def _build_selected_cho_details(focus_cho):
  cho = _find_cho(focus_cho)
  if cho is None:
    return None

  cho_refs = {str(cho.id)}
  if cho.custom_id:
    cho_refs.add(str(cho.custom_id))

  memory_rows = session.query(Memory).order_by(Memory.id).all()
  metadata_by_memory_id = _build_metadata_cache(memory_rows)
  memories = []

  for memory in memory_rows:
    tags = []
    for md in metadata_by_memory_id.get(memory.id, []):
      if md.get("type") == MetadataType.CHO.value and str(md.get("cho")) in cho_refs:
        tags.append({
          "field": md.get("field", ""),
          "value": md.get("value", ""),
        })

    if tags:
      memory_code = memory.custom_id or str(memory.id)
      memory_name = memory.title or f"Memory {memory.id}"
      memories.append({
        "memory_id": memory.id,
        "memory_label": f"{memory_code} - {memory_name}",
        "tags": tags,
      })

  return {
    "id": cho.id,
    "label": cho.custom_id or str(cho.id),
    "title": cho.title or cho.custom_id or str(cho.id),
    "memories": memories,
  }


def _strip_memory_metadata_block(text):
    return re.sub(
        r'===\s*MEMORY METADATA START\s*===.*?===\s*MEMORY METADATA END\s*===\s*',
        '',
        text or '',
        flags=re.DOTALL,
    )


def _remove_metadata_tag(text, field, metadata_type, cho=None):
    if metadata_type == MetadataType.MEMORY.value:
        pattern = re.compile(rf'(<{re.escape(field)}\s+type="memory">)(.*?)(</{re.escape(field)}>)', re.DOTALL)
    else:
        pattern = re.compile(rf'(<{re.escape(field)}\s+cho="{re.escape(cho or "")}">)(.*?)(</{re.escape(field)}>)', re.DOTALL)
    return pattern.sub(lambda match: match.group(2), text, count=1)


def _replace_metadata_tag(text, field, value, metadata_type, cho=None):
    if metadata_type == MetadataType.MEMORY.value:
        pattern = rf'<{re.escape(field)}\s+type="memory">.*?</{re.escape(field)}>'
        replacement = f'<{field} type="memory">{value}</{field}>'
    else:
        pattern = rf'<{re.escape(field)}\s+cho="{re.escape(cho or "")}">.*?</{re.escape(field)}>'
        replacement = f'<{field} cho="{cho}">{value}</{field}>'

    if re.search(pattern, text):
        return re.sub(pattern, replacement, text, count=1)
    if value:
        separator = "\n" if text and not text.endswith("\n") else ""
        return f"{text}{separator}{replacement}"
    return text


def _remove_all_cho_tags(text, cho_id):
  if not cho_id:
    return text
  pattern = re.compile(
    rf'<(?P<field>[a-zA-Z0-9:_-]+)\s+cho="{re.escape(str(cho_id))}">(?P<value>.*?)</(?P=field)>',
    re.DOTALL
  )
  return pattern.sub(lambda match: match.group("value"), text)


def _find_cho(cho_id):
    cho_text = str(cho_id or "").strip()
    if not cho_text:
        return None
    for cho in session.query(CHO).order_by(CHO.id):
        if str(cho.custom_id) == cho_text or str(cho.id) == cho_text:
            return cho
    return None


def _get_id(obj):
    return getattr(obj, "custom_id", obj)


def _safe_text(value):
    if callable(value) or value is None:
        return None
    return str(value)


def _indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def _create_rdf_root():
    return ET.Element("rdf:RDF", {
        "xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
        "xmlns:dcterms": "http://purl.org/dc/terms/",
        "xmlns:edm": "http://www.europeana.eu/schemas/edm/"
    })


def _export_memory_rdf_text(memory):
    mid = _get_id(memory)
    root = _create_rdf_root()

    desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/memory/{mid}"
    })
    ET.SubElement(desc, "rdf:type").text = "edm:WebResource"
    ET.SubElement(desc, "dc:identifier").text = str(mid)

    if memory.title:
      ET.SubElement(desc, "dc:title").text = memory.title

    metadata = extract_metadata(memory.text or "")
    cho_refs = set()

    for md in metadata:
        if md.get("type") == MetadataType.MEMORY.value:
            field = md.get("field")
            value = _safe_text(md.get("value"))
            if field and value:
                ET.SubElement(desc, field).text = value

    for md in metadata:
        if md.get("type") == MetadataType.CHO.value and md.get("cho"):
            cho_refs.add(md["cho"])

    for cho_id in sorted(cho_refs):
        ET.SubElement(desc, "edm:isRelatedTo").set(
            "rdf:resource",
            f"http://example.org/cho/{cho_id}"
        )

    _indent(root)
    return ET.tostring(root, encoding="unicode")


def _export_cho_rdf_single_memory_text(cho, memory):
    cho_id = _get_id(cho)
    root = _create_rdf_root()

    cho_desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/cho/{cho_id}"
    })
    ET.SubElement(cho_desc, "rdf:type").text = "edm:ProvidedCHO"
    ET.SubElement(cho_desc, "dc:identifier").text = _safe_text(cho_id)

    title = _safe_text(getattr(cho, "title", None))
    if title:
        ET.SubElement(cho_desc, "dc:title").text = title

    metadata = extract_metadata(memory.text or "")
    mem_uri = f"http://example.org/memory/{memory.custom_id}"

    contains = False
    part = ET.SubElement(cho_desc, "dcterms:hasPart")
    block = ET.SubElement(part, "rdf:Description", {"rdf:about": mem_uri})

    for md in metadata:
        if md.get("type") == MetadataType.CHO.value and str(md.get("cho")) == str(cho_id):
            field = md.get("field")
            value = _safe_text(md.get("value"))
            if field and value:
                contains = True
                ET.SubElement(cho_desc, field).text = value
                ET.SubElement(block, field).text = value

    web = ET.SubElement(block, "edm:WebResource")
    if memory.title:
        ET.SubElement(web, "dc:title").text = memory.title
    ET.SubElement(web, "dc:identifier").text = memory.custom_id
    ET.SubElement(block, "edm:isRelatedTo").set(
        "rdf:resource",
        f"http://example.org/cho/{cho_id}"
    )

    if not contains:
      cho_desc.remove(part)

    _indent(root)
    return ET.tostring(root, encoding="unicode")


def _export_cho_rdf_all_memories_text(cho):
    cho_id = _get_id(cho)
    root = _create_rdf_root()

    cho_desc = ET.SubElement(root, "rdf:Description", {
        "rdf:about": f"http://example.org/cho/{cho_id}"
    })
    ET.SubElement(cho_desc, "rdf:type").text = "edm:ProvidedCHO"
    ET.SubElement(cho_desc, "dc:identifier").text = _safe_text(cho_id)

    title = _safe_text(getattr(cho, "title", None))
    if title:
        ET.SubElement(cho_desc, "dc:title").text = title

    seen = set()
    for memory in session.query(Memory).order_by(Memory.id):
        metadata = extract_metadata(memory.text or "")
        mem_uri = f"http://example.org/memory/{memory.custom_id}"

        contains = False
        part = ET.SubElement(cho_desc, "dcterms:hasPart")
        block = ET.SubElement(part, "rdf:Description", {"rdf:about": mem_uri})

        for md in metadata:
            if md.get("type") == MetadataType.CHO.value and str(md.get("cho")) == str(cho_id):
                field = md.get("field")
                value = _safe_text(md.get("value"))
                if not field or not value:
                    continue
                contains = True
                if (field, value) not in seen:
                    ET.SubElement(cho_desc, field).text = value
                    seen.add((field, value))
                ET.SubElement(block, field).text = value

        web = ET.SubElement(block, "edm:WebResource")
        if memory.title:
            ET.SubElement(web, "dc:title").text = memory.title
        ET.SubElement(web, "dc:identifier").text = memory.custom_id
        ET.SubElement(block, "edm:isRelatedTo").set(
            "rdf:resource",
            f"http://example.org/cho/{cho_id}"
        )

        if not contains:
            cho_desc.remove(part)

    _indent(root)
    return ET.tostring(root, encoding="unicode")


def _rdf_download_response(rdf_text, file_name):
    return Response(
        rdf_text,
        mimetype="application/rdf+xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'}
    )


def _build_search_snippet(text, term, radius=80):
    clean_text, _ = parse_text_and_spans(text or "")
    flattened = re.sub(r"\s+", " ", clean_text).strip()
    if not flattened:
        return ""

    term_text = (term or "").strip()
    if not term_text:
        return flattened[:170] + ("..." if len(flattened) > 170 else "")

    lower_text = flattened.lower()
    lower_term = term_text.lower()
    idx = lower_text.find(lower_term)

    if idx == -1:
        return flattened[:170] + ("..." if len(flattened) > 170 else "")

    start = max(0, idx - radius)
    end = min(len(flattened), idx + len(term_text) + radius)
    snippet = flattened[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(flattened):
        snippet = snippet + "..."
    return snippet

def _redirect_with_notice(endpoint, level, message, **kwargs):
  kwargs["notice_level"] = level
  kwargs["notice_message"] = message
  return redirect(url_for(endpoint, **kwargs))


def create_app(testing=False):
  app = Flask(__name__)
  app.config["TESTING"] = testing

  @app.route("/")
  def index():
    memory_id = request.args.get("memory_id", type=int)
    focus_cho = request.args.get("focus_cho", "")
    notice_level = request.args.get("notice_level", "").strip() or "success"
    notice_message = request.args.get("notice_message", "").strip()
    memories, chos, selected_memory, metadata, paragraphs, memory_metadata_items, cho_metadata_items, _ = _load_context(memory_id, focus_cho)
    nodes, edges = _build_graph_data(memory_id, focus_cho)
    selected_cho_details = _build_selected_cho_details(focus_cho) if focus_cho else None
    return render_template_string(
      HTML_TEMPLATE,
      memories=memories,
      chos=chos,
      selected_memory=selected_memory,
      metadata=metadata,
      paragraphs=paragraphs,
      memory_metadata_items=memory_metadata_items,
      cho_metadata_items=cho_metadata_items,
      cho_fields=CHO_FIELDS,
      memory_fields=MEMORY_FIELDS,
      memory_license_options=MEMORY_LICENSE_OPTIONS,
      nodes=nodes,
      edges=edges,
      focus_cho=focus_cho,
      focus_memory=f"memory:{memory_id}" if memory_id else "",
      selected_cho_details=selected_cho_details,
      notice_level=notice_level,
      notice_message=notice_message,
    )

  @app.route("/memories/import", methods=["GET", "POST"])
  def import_memory():
    notice_level = request.args.get("notice_level", "").strip() or "success"
    notice_message = request.args.get("notice_message", "").strip()
    import_ready = False
    temp_path = ""
    suggested_id = request.args.get("id", "").strip()
    form_metadata = {field: "" for field in IMPORT_FIELDS}
    form_metadata[MEMORY_LICENSE_FIELD] = ""
    detected_count = 0

    if request.method == "POST":
      stage = request.form.get("stage", "prepare").strip().lower()

      if stage == "prepare":
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
          return _redirect_with_notice("import_memory", "error", "Please select a .txt file to import.")
        if not uploaded.filename.lower().endswith(".txt"):
          return _redirect_with_notice("import_memory", "error", "Invalid file type. Please upload a .txt file.")

        suggested_id = request.form.get("id", "").strip() or str(uuid.uuid4())[:8]
        with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
          uploaded.save(handle.name)
          temp_path = handle.name

        with open(temp_path, encoding="utf-8", errors="replace") as handle:
          txt = handle.read()
        txt = html.unescape(txt)
        txt = re.sub(r"<rdf:RDF.*?</rdf:RDF>", "", txt, flags=re.DOTALL)
        with open(temp_path, "w", encoding="utf-8") as handle:
          handle.write(txt)

        existing_memory_md = _extract_memory_block_metadata(txt)
        for field in IMPORT_FIELDS:
          form_metadata[field] = existing_memory_md.get(field, "")
        form_metadata[MEMORY_LICENSE_FIELD] = existing_memory_md.get(MEMORY_LICENSE_FIELD, "")

        suggested_id = request.form.get("id", "").strip() or existing_memory_md.get("dc:identifier", "") or str(uuid.uuid4())[:8]
        import_ready = True
        detected_count = len(existing_memory_md)
        notice_level = "success"
        notice_message = "File loaded. Existing memory metadata has been prefilled."

      elif stage == "confirm":
        temp_path = request.form.get("temp_path", "").strip()
        if not temp_path or not os.path.exists(temp_path):
          return _redirect_with_notice("import_memory", "error", "Import session expired. Please upload the file again.")

        suggested_id = request.form.get("id", "").strip()
        if not suggested_id:
          with open(temp_path, encoding="utf-8", errors="replace") as handle:
            txt = handle.read()
          existing_memory_md = _extract_memory_block_metadata(txt)
          suggested_id = existing_memory_md.get("dc:identifier", "").strip() or str(uuid.uuid4())[:8]
        else:
          with open(temp_path, encoding="utf-8", errors="replace") as handle:
            txt = handle.read()
        if session.query(Memory).filter(Memory.custom_id == suggested_id).first() is not None:
          notice_level = "error"
          notice_message = f"Memory ID '{suggested_id}' already exists. Choose another ID."
          import_ready = True
          existing_memory_md = _extract_memory_block_metadata(txt)
          detected_count = len(existing_memory_md)
          for field in IMPORT_FIELDS:
            form_metadata[field] = request.form.get(field, "").strip() or existing_memory_md.get(field, "")
          form_metadata[MEMORY_LICENSE_FIELD] = request.form.get(MEMORY_LICENSE_FIELD, "").strip() or existing_memory_md.get(MEMORY_LICENSE_FIELD, "")
        else:
          try:
            existing_memory_md = _extract_memory_block_metadata(txt)
            metadata = dict(existing_memory_md)
            for field in IMPORT_FIELDS:
              value = request.form.get(field, "").strip()
              if value:
                metadata[field] = value

            license_value = request.form.get(MEMORY_LICENSE_FIELD, "").strip() or metadata.get(MEMORY_LICENSE_FIELD, "")
            if license_value:
              metadata[MEMORY_LICENSE_FIELD] = license_value

            metadata["dc:identifier"] = suggested_id

            final_text = rebuild_memory_text(txt, metadata, suggested_id)
            stored_path = _write_memory_text_file(suggested_id, final_text)
            memory = Memory(
              custom_id=suggested_id,
              title=metadata.get("dc:title", suggested_id),
              text=final_text,
              file_path=stored_path,
              license=metadata.get(MEMORY_LICENSE_FIELD, "") or None,
            )
            session.add(memory)
            session.commit()
          finally:
            if temp_path and os.path.exists(temp_path):
              os.remove(temp_path)

          preserved_count = len(existing_memory_md)
          if preserved_count:
            return _redirect_with_notice(
              "index",
              "success",
              f"Memory imported successfully. Preserved {preserved_count} existing memory metadata fields.",
              memory_id=memory.id,
            )

          return _redirect_with_notice("index", "success", "Memory imported successfully.", memory_id=memory.id)

    return render_template_string(
      IMPORT_TEMPLATE,
      notice_level=notice_level,
      notice_message=notice_message,
      import_ready=import_ready,
      temp_path=temp_path,
      suggested_id=suggested_id,
      form_metadata=form_metadata,
      detected_count=detected_count,
      memory_license_options=MEMORY_LICENSE_OPTIONS,
    )

  @app.route("/memories/<int:memory_id>/edit", methods=["POST"])
  def edit_memory(memory_id):
    memory = session.get(Memory, memory_id)
    if memory is None:
      return _redirect_with_notice("index", "error", "Memory not found.")

    focus_cho = request.form.get("focus_cho", "").strip()
    if "title" in request.form:
      memory.title = request.form.get("title", "").strip() or (memory.title or f"Memory {memory.id}")

    posted_text = request.form.get("text")
    updated_text = posted_text if posted_text is not None else (memory.text or "")
    memory_metadata_ops = False
    current_memory_license = _memory_license_value(memory)
    if "memory_license" in request.form:
      memory_license_value = request.form.get("memory_license", "").strip()
    else:
      memory_license_value = current_memory_license
    if request.form.get("save_memory_license") or memory_license_value != current_memory_license:
      memory_metadata_ops = True

    deleted_memory_fields = set()
    deleted_cho_fields = set()
    deleted_cho_indices = set()
    metadata_map = _memory_metadata_dict(updated_text)
    if memory_license_value:
      metadata_map[MEMORY_LICENSE_FIELD] = memory_license_value
    else:
      metadata_map.pop(MEMORY_LICENSE_FIELD, None)

    for key in request.form:
      if key.startswith("delete_memory_metadata[") and key.endswith("]"):
        memory_metadata_ops = True
        field = key[len("delete_memory_metadata["):-1]
        deleted_memory_fields.add(field)
        metadata_map.pop(field, None)
        updated_text = _remove_metadata_tag(updated_text, field, MetadataType.MEMORY.value)
      elif key.startswith("delete_cho_metadata[") and "]" in key:
        if key.endswith("]"):
          remainder = key[len("delete_cho_metadata["):-1]
          if "][" in remainder:
            cho_id, field = remainder.split("][", 1)
            deleted_cho_fields.add((cho_id, field))
            updated_text = _remove_metadata_tag(updated_text, field, MetadataType.CHO.value, cho=cho_id)
          else:
            deleted_cho_indices.add(remainder)
            updated_text = _remove_nth_cho_tag(updated_text, remainder)
      elif key == "delete_memory_metadata" and request.form.get(key):
        memory_metadata_ops = True
        metadata_map.pop(request.form.get(key), None)
      elif key == "delete_cho_metadata" and request.form.get(key):
        updated_text = _remove_metadata_tag(updated_text, request.form.get(key), MetadataType.CHO.value)

    for key, value in request.form.items():
      if key.startswith("memory_metadata[") and key.endswith("]"):
        memory_metadata_ops = True
        field = key[len("memory_metadata["):-1]
        if field in deleted_memory_fields:
          continue
        if value is not None and str(value).strip():
          metadata_map[field] = str(value).strip()
        else:
          metadata_map.pop(field, None)
      elif key.startswith("cho_metadata[") and "]" in key:
        remainder = key[len("cho_metadata["):]
        cho_id, field = remainder.split("][")
        field = field[:-1]
        if (cho_id, field) in deleted_cho_fields:
          continue
        updated_text = _replace_metadata_tag(updated_text, field, value, MetadataType.CHO.value, cho=cho_id)

    edit_field = request.form.get("edit_memory_metadata_field", "").strip()
    edit_value = request.form.get("edit_memory_metadata_value", "").strip()
    if edit_field and edit_field not in deleted_memory_fields and edit_value:
      memory_metadata_ops = True
      metadata_map[edit_field] = edit_value

    if request.form.get("new_memory_metadata_field") and request.form.get("new_memory_metadata_value", "").strip():
      memory_metadata_ops = True
      metadata_map[request.form.get("new_memory_metadata_field", "").strip()] = request.form.get("new_memory_metadata_value", "").strip()

    if MEMORY_LICENSE_FIELD in deleted_memory_fields:
      memory_license_value = ""

    if memory_metadata_ops:
      if metadata_map:
        updated_text = rebuild_memory_text(updated_text, metadata_map, memory.custom_id or memory.id)
      else:
        updated_text = _strip_memory_metadata_block(updated_text).strip()

    _persist_memory_to_disk(memory, updated_text)
    memory.license = memory_license_value or None
    if "title" not in request.form:
      memory.title = get_memory_title(memory.text or "", memory.title or f"Memory {memory.id}")
    session.add(memory)
    session.commit()
    redirect_kwargs = {"memory_id": memory_id}
    if focus_cho:
      redirect_kwargs["focus_cho"] = focus_cho
    return _redirect_with_notice("index", "success", "Memory metadata saved.", **redirect_kwargs)

  @app.route("/memories/<int:memory_id>/annotate", methods=["POST"])
  def annotate_memory(memory_id):
    memory = session.get(Memory, memory_id)
    if memory is None:
      return _redirect_with_notice("index", "error", "Memory not found.")

    focus_cho = request.form.get("focus_cho", "").strip()

    annotation_text = request.form.get("selected_annotation_text", "").strip() or request.form.get("annotation_text", "").strip()
    selected_occurrence = request.form.get("selected_annotation_occurrence", type=int)
    if selected_occurrence is None:
      selected_occurrence = 0
    annotation_field = request.form.get("annotation_field", "").strip()
    annotation_cho = request.form.get("annotation_cho", "").strip()
    if annotation_text and annotation_field and annotation_cho:
      annotation_open = f'<{annotation_field} cho="{annotation_cho}">'
      annotation_close = f'</{annotation_field}>'
      current_text = memory.text or ""
      clean_text, _ = parse_text_and_spans(current_text)
      visible_start = _find_nth_occurrence(clean_text, annotation_text, selected_occurrence)
      if visible_start == -1:
        visible_start = clean_text.find(annotation_text)

      if visible_start != -1:
        visible_end = visible_start + len(annotation_text)
        raw_span = _visible_span_to_raw_span(current_text, visible_start, visible_end)
        if raw_span is not None:
          raw_start, raw_end = raw_span
          wrapped_segment = current_text[raw_start:raw_end]
          memory.text = (
            current_text[:raw_start]
            + annotation_open
            + wrapped_segment
            + annotation_close
            + current_text[raw_end:]
          )
        else:
          memory.text = current_text.replace(annotation_text, f"{annotation_open}{annotation_text}{annotation_close}", 1)
      elif annotation_text in current_text:
        memory.text = current_text.replace(annotation_text, f"{annotation_open}{annotation_text}{annotation_close}", 1)
      else:
        memory.text = current_text + ("\n" if current_text else "") + annotation_open + annotation_text + annotation_close
      _persist_memory_to_disk(memory)
      session.add(memory)
      session.commit()
      redirect_kwargs = {"memory_id": memory_id}
      if focus_cho:
        redirect_kwargs["focus_cho"] = focus_cho
      return _redirect_with_notice("index", "success", "Annotation added.", **redirect_kwargs)

    redirect_kwargs = {"memory_id": memory_id}
    if focus_cho:
      redirect_kwargs["focus_cho"] = focus_cho
    return _redirect_with_notice("index", "error", "Select text and provide CHO and field before adding an annotation.", **redirect_kwargs)

  @app.route("/memories/<int:memory_id>/delete", methods=["POST"])
  def delete_memory(memory_id):
    memory = session.get(Memory, memory_id)
    if memory is not None:
      file_path = memory.file_path
      memory_label = memory.title or memory.custom_id or f"Memory {memory.id}"
      session.delete(memory)
      session.commit()
      if file_path and os.path.exists(file_path):
        try:
          os.remove(file_path)
        except OSError:
          pass
      return _redirect_with_notice("index", "success", f"Deleted memory: {memory_label}.")
    return _redirect_with_notice("index", "error", "Memory not found.")

  @app.route("/chos/create", methods=["POST"])
  def create_cho():
    custom_id = request.form.get("custom_id", "").strip()
    title = request.form.get("title", "").strip()
    memory_id = request.form.get("memory_id", type=int)
    if not custom_id:
      return _redirect_with_notice("index", "error", "CHO ID is required.", memory_id=memory_id)
    if session.query(CHO).filter(CHO.custom_id == custom_id).first() is not None:
      return _redirect_with_notice("index", "error", f"CHO ID '{custom_id}' already exists.", memory_id=memory_id)

    cho = CHO(custom_id=custom_id, title=title or custom_id)
    session.add(cho)
    session.commit()
    return _redirect_with_notice("index", "success", f"Created CHO: {custom_id}.", memory_id=memory_id)

  @app.route("/chos/<int:cho_db_id>/delete", methods=["POST"])
  def delete_cho(cho_db_id):
    memory_id = request.args.get("memory_id", type=int)
    cho = session.get(CHO, cho_db_id)
    if cho is not None:
      cho_label = cho.custom_id or str(cho.id)
      cho_refs = {str(cho.id)}
      if cho.custom_id:
        cho_refs.add(str(cho.custom_id))

      for memory in session.query(Memory).order_by(Memory.id):
        updated = memory.text or ""
        for cho_ref in cho_refs:
          updated = _remove_all_cho_tags(updated, cho_ref)
        _persist_memory_to_disk(memory, updated)
        session.add(memory)

      session.delete(cho)
      session.commit()
      return _redirect_with_notice("index", "success", f"Deleted CHO: {cho_label}.", memory_id=memory_id)
    return _redirect_with_notice("index", "error", "CHO not found.", memory_id=memory_id)

  @app.route("/graph")
  def graph():
    memory_id = request.args.get("memory_id", type=int)
    focus_cho = request.args.get("focus_cho", "")
    memories, chos, selected_memory, metadata, paragraphs, memory_metadata_items, cho_metadata_items, _ = _load_context(memory_id, focus_cho)
    nodes, edges = _build_graph_data(memory_id, focus_cho)
    selected_cho_details = _build_selected_cho_details(focus_cho) if focus_cho else None
    return render_template_string(
      HTML_TEMPLATE,
      memories=memories,
      chos=chos,
      selected_memory=selected_memory,
      metadata=metadata,
      paragraphs=paragraphs,
      memory_metadata_items=memory_metadata_items,
      cho_metadata_items=cho_metadata_items,
      cho_fields=CHO_FIELDS,
      memory_fields=MEMORY_FIELDS,
      memory_license_options=MEMORY_LICENSE_OPTIONS,
      nodes=nodes,
      edges=edges,
      focus_cho=focus_cho,
      focus_memory=f"memory:{memory_id}" if memory_id else "",
      selected_cho_details=selected_cho_details,
      notice_level=request.args.get("notice_level", "").strip() or "success",
      notice_message=request.args.get("notice_message", "").strip(),
    )

  @app.route("/search")
  def search_memories():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", default=1, type=int) or 1
    page = max(page, 1)
    result_rows = []
    total_results = 0
    total_pages = 1
    if q:
      query = session.query(Memory).filter(
        Memory.text.ilike(f"%{q}%")
      ).order_by(Memory.id)
      total_results = query.count()
      total_pages = max(1, (total_results + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE)
      page = min(page, total_pages)
      offset = (page - 1) * SEARCH_PAGE_SIZE
      page_results = query.offset(offset).limit(SEARCH_PAGE_SIZE).all()
      result_rows = [
        {
          "id": memory.id,
          "custom_id": memory.custom_id,
          "title": memory.title,
          "snippet": _build_search_snippet(memory.text or "", q),
        }
        for memory in page_results
      ]
    return render_template_string(
      SEARCH_TEMPLATE,
      q=q,
      result_rows=result_rows,
      total_results=total_results,
      page=page,
      total_pages=total_pages,
      searched=bool(request.args),
    )

  @app.route("/compare")
  def compare_cho():
    chos = session.query(CHO).order_by(CHO.id).all()
    selected_cho = request.args.get("cho_id", "").strip()
    memory_columns = []
    matrix_rows = []
    metadata_by_memory_id = _build_metadata_cache(session.query(Memory).order_by(Memory.id).all())

    if selected_cho:
      field_memory_values = {}
      for memory in session.query(Memory).order_by(Memory.id):
        memory_label = f"{memory.custom_id or memory.id} - {memory.title or ('Memory ' + str(memory.id))}"
        memory_columns.append({"id": memory.id, "label": memory_label})
        for md in metadata_by_memory_id.get(memory.id, []):
          if md.get("type") == MetadataType.CHO.value and str(md.get("cho")) == selected_cho:
            field = md.get("field", "")
            value = md.get("value", "")
            if not field:
              continue
            memory_map = field_memory_values.setdefault(field, {})
            existing = memory_map.get(memory.id, "")
            memory_map[memory.id] = f"{existing}; {value}" if existing else value

      matrix_rows = [
        {"field": field, "values": values}
        for field, values in sorted(field_memory_values.items())
      ]

      if matrix_rows:
        used_memory_ids = {
          mem_id
          for row in matrix_rows
          for mem_id, val in row["values"].items()
          if val
        }
        memory_columns = [col for col in memory_columns if col["id"] in used_memory_ids]

    return render_template_string(
      COMPARE_TEMPLATE,
      chos=chos,
      selected_cho=selected_cho,
      memory_columns=memory_columns,
      matrix_rows=matrix_rows,
      field_descriptions={row["field"]: _metadata_description(row["field"]) for row in matrix_rows},
    )

  @app.route("/export/memory/<int:memory_id>.rdf")
  def export_memory_rdf(memory_id):
    memory = session.get(Memory, memory_id)
    if memory is None:
      return redirect(url_for("index"))
    rdf = _export_memory_rdf_text(memory)
    file_name = f"memory_{memory.custom_id or memory.id}.rdf"
    return _rdf_download_response(rdf, file_name)

  @app.route("/export/cho")
  def export_cho_rdf():
    cho_id = request.args.get("cho_id", "").strip()
    mode = request.args.get("mode", "all").strip().lower()
    memory_id = request.args.get("memory_id", type=int)

    cho = _find_cho(cho_id)
    if cho is None:
      return redirect(url_for("compare_cho"))

    cho_ref = str(cho.custom_id or cho.id)
    if mode == "single":
      memory = session.get(Memory, memory_id) if memory_id else None
      if memory is None:
        for candidate in session.query(Memory).order_by(Memory.id):
          if any(
            md.get("type") == MetadataType.CHO.value and str(md.get("cho")) == cho_ref
            for md in extract_metadata(candidate.text or "")
          ):
            memory = candidate
            break
      if memory is None:
        return redirect(url_for("compare_cho", cho_id=cho_ref))
      rdf = _export_cho_rdf_single_memory_text(cho, memory)
      file_name = f"cho_{cho_ref}_single.rdf"
    else:
      rdf = _export_cho_rdf_all_memories_text(cho)
      file_name = f"cho_{cho_ref}_all.rdf"

    return _rdf_download_response(rdf, file_name)

  @app.route("/health")
  def health():
    return {"status": "ok"}

  return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)