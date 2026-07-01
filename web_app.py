import html
import os
import re
import tempfile
import uuid

from flask import Flask, redirect, render_template_string, request, url_for

from db import CHO, Memory, session
from services.file_service import copy_memory_file
from services.memory_service import rebuild_memory_text
from services.metadata import extract_metadata, get_memory_title, parse_text_and_spans
from services.metadata_schema import METADATA_FIELDS
from services.types import MetadataType


CHO_FIELDS = [
    {"field": field, "label": meta.get("label", field)}
    for category in ("CHO", "Agent")
    for field, meta in METADATA_FIELDS.get(category, {}).get("fields", {}).items()
]


HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CORDHISK Web</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; background: #f4f7fb; color: #1f2937; }
      .shell { display: grid; grid-template-columns: 300px 1fr; min-height: 100vh; }
      .sidebar { background: #0f172a; color: white; padding: 20px; }
      .content { padding: 24px; }
      .card { background: white; border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
      a { color: #2563eb; text-decoration: none; }
      .pill { display: inline-block; margin: 3px; padding: 4px 8px; border-radius: 999px; background: #e2e8f0; font-size: 12px; }
      .pill.memory { background: #dbeafe; color: #1d4ed8; }
      .pill.cho { background: #dcfce7; color: #166534; }
      .text-view { font-family: inherit; line-height: 1.7; white-space: normal; }
      .text-view p { margin: 0 0 10px; }
      form input, form select, form textarea { width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
      form textarea { min-height: 140px; }
      button { padding: 8px 12px; border: 0; border-radius: 6px; background: #2563eb; color: white; cursor: pointer; }
      .nav { margin-bottom: 14px; }
      .nav a { color: white; margin-right: 10px; }
      .highlight { padding: 0 2px; border-radius: 4px; color: #111827; }
      .highlight.memory { background: #fef3c7; }
      .highlight.cho { background: #bfdbfe; }
      .metadata-panel { margin: 14px 0 18px; }
      .metadata-panel summary { cursor: pointer; font-weight: 600; margin-bottom: 8px; }
      .metadata-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
      .metadata-section { border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; }
      .metadata-table { width: 100%; border-collapse: collapse; font-size: 13px; }
      .metadata-table th, .metadata-table td { text-align: left; padding: 6px 4px; border-bottom: 1px solid #eef2f7; }
      .metadata-table input { margin-bottom: 0; }
      .annotation-toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
      .annotation-toolbar button { padding: 6px 10px; }
      .graph-toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 12px; }
      .graph-toolbar button { padding: 6px 10px; }
      .graph-detail-panel { margin-top: 10px; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; min-height: 56px; }
      .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 0.8fr); gap: 16px; }
      .graph-card { min-height: 780px; }
      .graph-shell { overflow: auto; border: 1px solid #dbe4f0; border-radius: 8px; background: white; }
      svg { width: 100%; min-width: 1000px; height: auto; border: 0; border-radius: 8px; background: white; cursor: grab; }
      svg.dragging { cursor: grabbing; }
      .node { stroke: #334155; stroke-width: 1.5; }
      .memory { fill: #60a5fa; }
      .cho { fill: #34d399; }
      .memory_metadata { fill: #a3e635; }
      .cho_metadata { fill: #f59e0b; }
      .graph-node.metadata-hidden { opacity: 0; visibility: hidden; pointer-events: none; }
      .graph-node.metadata-visible { opacity: 1; visibility: visible; pointer-events: auto; }
      .focused { stroke: #ef4444; stroke-width: 3; }
      .label { font-size: 12px; fill: #0f172a; }
    </style>
  </head>
  <body>
    <div class="shell">
      <aside class="sidebar">
        <h2>CORDHISK</h2>
        <p>Web-based metadata workspace for memories and cultural heritage objects.</p>
        <div class="nav">
          <a href="/">Dashboard</a>
          <a href="/memories/import">Import memory</a>
        </div>
        <div class="card">
          <h3>Memories</h3>
          <ul>
            {% for memory in memories %}
            <li><a href="/?memory_id={{ memory.id }}">{{ memory.custom_id or memory.id }} — {{ memory.title or ('Memory ' ~ memory.id) }}</a></li>
            {% endfor %}
          </ul>
        </div>
        <div class="card">
          <h3>CHO records</h3>
          <ul>
            {% for cho in chos %}
            <li><a href="/?memory_id={{ selected_memory.id if selected_memory else '' }}&focus_cho={{ cho.custom_id or cho.id }}">{{ cho.custom_id or cho.id }} — {{ cho.title or cho.custom_id or cho.id }}</a></li>
            {% endfor %}
          </ul>
        </div>
      </aside>
      <main class="content">
        <div class="card">
          <h1>CORDHISK Web Interface</h1>
          <p>This prototype preserves the existing database-driven logic and now exposes import, metadata editing, annotation, and graph workflows in the browser.</p>
        </div>
        {% if selected_memory %}
        <div class="grid">
          <div class="card">
            <h2>{{ selected_memory.title or ('Memory ' ~ selected_memory.id) }}</h2>
            <p><strong>Source file:</strong> {{ selected_memory.file_path or 'n/a' }}</p>
            <div>
              {% for md in metadata %}
              <span class="pill {{ md.type }}">{{ md.field }}: {{ md.value }}</span>
              {% endfor %}
            </div>
            <form action="/memories/{{ selected_memory.id }}/edit" method="post">
              <label>Title</label>
              <input name="title" value="{{ selected_memory.title or '' }}">
              <details class="metadata-panel" open>
                <summary>Editable metadata</summary>
                <div class="metadata-grid">
                  <div class="metadata-section">
                    <h4>Memory metadata</h4>
                    <table class="metadata-table">
                      <thead><tr><th>Field</th><th>Value</th></tr></thead>
                      <tbody>
                        {% for md in memory_metadata_items %}
                        <tr>
                          <td>{{ md.field }}</td>
                          <td><input name="memory_metadata[{{ md.field }}]" value="{{ md.value }}"></td>
                          <td><label><input type="checkbox" name="delete_memory_metadata[{{ md.field }}]" value="1"> delete</label></td>
                        </tr>
                        {% else %}
                        <tr><td colspan="3">No memory metadata available.</td></tr>
                        {% endfor %}
                      </tbody>
                    </table>
                    <div class="metadata-section">
                      <h5>Add memory metadata</h5>
                      <label>Field</label>
                      <input name="new_memory_metadata_field" placeholder="dc:title">
                      <label>Value</label>
                      <input name="new_memory_metadata_value" placeholder="New value">
                      <button type="submit" name="add_memory_metadata" value="1">Add memory metadata</button>
                    </div>
                    <button type="submit" name="delete_selected_metadata" value="1">Delete selected metadata</button>
                  </div>
                  <div class="metadata-section">
                    <h4>CHO metadata</h4>
                    <table class="metadata-table">
                      <thead><tr><th>CHO / field</th><th>Value</th></tr></thead>
                      <tbody>
                        {% for md in cho_metadata_items %}
                        <tr>
                          <td>{{ md.cho }} / {{ md.field }}</td>
                          <td><input name="cho_metadata[{{ md.cho }}][{{ md.field }}]" value="{{ md.value }}"></td>
                          <td><label><input type="checkbox" name="delete_cho_metadata[{{ md.cho }}][{{ md.field }}]" value="1"> delete</label></td>
                        </tr>
                        {% else %}
                        <tr><td colspan="3">No CHO metadata available.</td></tr>
                        {% endfor %}
                      </tbody>
                    </table>
                    <div class="metadata-section">
                      <h5>Add CHO metadata</h5>
                      <label>CHO</label>
                      <select name="new_cho_metadata_cho">
                        {% for cho in chos %}
                        <option value="{{ cho.custom_id or cho.id }}">{{ cho.title or cho.custom_id or cho.id }}</option>
                        {% endfor %}
                      </select>
                      <label>Field</label>
                      <input name="new_cho_metadata_field" placeholder="dc:title">
                      <label>Value</label>
                      <input name="new_cho_metadata_value" placeholder="New value">
                      <button type="submit" name="add_cho_metadata" value="1">Add CHO metadata</button>
                    </div>
                  </div>
                </div>
              </details>
              <details class="metadata-panel">
                <summary>Show raw tag editor</summary>
                <label>Text (raw tags)</label>
                <textarea name="text">{{ selected_memory.text or '' }}</textarea>
              </details>
              <button type="submit">Save memory</button>
            </form>
            <form action="/memories/{{ selected_memory.id }}/annotate" method="post">
              <h3>Annotate highlighted memory text</h3>
              <p>Select text in the highlighted visualisation below, then wrap it as a metadata annotation.</p>
              <div class="annotation-toolbar">
                <button type="button" id="capture-selection">Use selected text</button>
                <span id="selection-preview">No selection yet</span>
              </div>
              <div id="annotation-source" class="text-view" style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin-bottom: 10px; user-select: text;">
                {% for paragraph in paragraphs %}
                <p>
                  {% for part in paragraph %}
                    {% if part.type == 'text' %}
                      {{ part.value }}
                    {% else %}
                      <span class="highlight {{ part.kind }}" title="{{ part.field }}">{{ part.value }}</span>
                    {% endif %}
                  {% endfor %}
                </p>
                {% endfor %}
              </div>
              <input id="selected-annotation-text" name="selected_annotation_text" placeholder="Selected text will appear here">
              <label>CHO</label>
              <select name="annotation_cho">
                {% for cho in chos %}
                <option value="{{ cho.custom_id or cho.id }}">{{ cho.title or cho.custom_id or cho.id }}</option>
                {% endfor %}
              </select>
              <label>Field</label>
              <select name="annotation_field">
                {% for field in cho_fields %}
                <option value="{{ field.field }}">{{ field.label }}</option>
                {% endfor %}
              </select>
              <button type="submit">Add annotation</button>
            </form>
          </div>
          <div class="card graph-card">
            <h3>Memory relationship graph</h3>
            <p>Click a memory node to reveal its metadata and hover a CHO node to inspect its metadata.</p>
            <div class="graph-toolbar">
              <button type="button" id="zoom-in">Zoom in</button>
              <button type="button" id="zoom-out">Zoom out</button>
              <button type="button" id="reset-view">Reset view</button>
            </div>
            <div class="graph-shell">
              <svg id="graph-svg" viewBox="0 0 1000 700" role="img" aria-label="Memory and CHO graph">
                <g id="graph-content">
                  {% for edge in edges %}
                  <line x1="{{ edge[0].x }}" y1="{{ edge[0].y }}" x2="{{ edge[1].x }}" y2="{{ edge[1].y }}" stroke="#94a3b8" stroke-width="2"></line>
                  {% endfor %}
                  {% for node in nodes %}
                  <a href="{{ node.link }}">
                    <circle class="graph-node node {{ node.group }} {% if node.id == ('cho:' ~ focus_cho) or node.id == focus_memory %}focused{% endif %} {% if node.group in ['memory_metadata','cho_metadata'] %}metadata-hidden{% endif %}" data-node-type="{{ node.group }}" data-parent-id="{{ node.parent_id or '' }}" data-details="{{ node.details or '' }}" title="{{ node.details or '' }}" cx="{{ node.x }}" cy="{{ node.y }}" r="{{ node.radius or 32 }}"></circle>
                    <text class="label" x="{{ node.x }}" y="{{ node.y + 6 }}" text-anchor="middle">{{ node.label }}</text>
                  </a>
                  {% endfor %}
                </g>
              </svg>
            </div>
            <div id="graph-detail-panel" class="graph-detail-panel">Hover over a CHO node or click a memory node to inspect its metadata.</div>
          </div>
        </div>
        {% else %}
        <div class="card">
          <p>Select a memory from the left to see its content and extracted metadata.</p>
        </div>
        {% endif %}
      </main>
    </div>
    <script>
      document.addEventListener('DOMContentLoaded', function () {
        const source = document.getElementById('annotation-source');
        const target = document.getElementById('selected-annotation-text');
        const preview = document.getElementById('selection-preview');
        const button = document.getElementById('capture-selection');
        const svg = document.getElementById('graph-svg');
        const graphContent = document.getElementById('graph-content');
        const detailPanel = document.getElementById('graph-detail-panel');
        const zoomInButton = document.getElementById('zoom-in');
        const zoomOutButton = document.getElementById('zoom-out');
        const resetButton = document.getElementById('reset-view');
        let zoomLevel = 1;
        let panX = 0;
        let panY = 0;
        let isDragging = false;
        let startX = 0;
        let startY = 0;

        function captureSelection() {
          const selection = window.getSelection().toString().trim();
          if (!selection) {
            preview.textContent = 'No selection yet';
            return;
          }
          target.value = selection;
          preview.textContent = 'Selection: ' + selection;
        }

        if (button && source && target && preview) {
          button.addEventListener('click', captureSelection);
          source.addEventListener('mouseup', function () { setTimeout(captureSelection, 0); });
        }

        function applyTransform() {
          if (graphContent) {
            graphContent.setAttribute('transform', `translate(${panX} ${panY}) scale(${zoomLevel})`);
          }
        }

        if (svg && graphContent) {
          const updateZoom = (factor) => {
            zoomLevel = Math.max(0.7, Math.min(2.4, zoomLevel * factor));
            applyTransform();
          };

          if (zoomInButton) {
            zoomInButton.addEventListener('click', function () { updateZoom(1.15); });
          }
          if (zoomOutButton) {
            zoomOutButton.addEventListener('click', function () { updateZoom(0.85); });
          }
          if (resetButton) {
            resetButton.addEventListener('click', function () {
              zoomLevel = 1;
              panX = 0;
              panY = 0;
              applyTransform();
            });
          }

          svg.addEventListener('wheel', function (event) {
            event.preventDefault();
            if (event.deltaY < 0) {
              updateZoom(1.05);
            } else {
              updateZoom(0.95);
            }
          }, { passive: false });

          svg.addEventListener('mousedown', function (event) {
            if (event.target.tagName === 'svg' || event.target.tagName === 'circle' || event.target.tagName === 'text') {
              isDragging = true;
              svg.classList.add('dragging');
              startX = event.clientX;
              startY = event.clientY;
            }
          });
          window.addEventListener('mousemove', function (event) {
            if (!isDragging) {
              return;
            }
            panX += event.clientX - startX;
            panY += event.clientY - startY;
            startX = event.clientX;
            startY = event.clientY;
            applyTransform();
          });
          window.addEventListener('mouseup', function () {
            isDragging = false;
            svg.classList.remove('dragging');
          });

          const metadataNodes = Array.from(document.querySelectorAll('.graph-node[data-node-type="memory_metadata"], .graph-node[data-node-type="cho_metadata"]'));
          const hideMetadataNodes = () => {
            metadataNodes.forEach((mdNode) => {
              mdNode.classList.remove('metadata-visible');
              mdNode.classList.add('metadata-hidden');
            });
          };
          const showMetadataNodesFor = (parentId, nodeType) => {
            hideMetadataNodes();
            if (nodeType !== 'cho') {
              return;
            }
            metadataNodes.forEach((mdNode) => {
              const isChoMetadata = mdNode.getAttribute('data-node-type') === 'cho_metadata';
              const visible = isChoMetadata && mdNode.getAttribute('data-parent-id') === parentId;
              mdNode.classList.toggle('metadata-visible', visible);
              mdNode.classList.toggle('metadata-hidden', !visible);
            });
          };

          const nodeElements = Array.from(document.querySelectorAll('.graph-node'));
          nodeElements.forEach((node) => {
            node.addEventListener('mouseenter', function () {
              const parentId = node.getAttribute('data-parent-id');
              const nodeType = node.getAttribute('data-node-type');
              if (nodeType === 'cho' || nodeType === 'memory') {
                showMetadataNodesFor(parentId, nodeType);
              }
              if (detailPanel) {
                detailPanel.textContent = node.getAttribute('data-details') || 'No metadata details available.';
              }
            });
            node.addEventListener('mouseleave', function () {
              const nodeType = node.getAttribute('data-node-type');
              if (nodeType === 'cho' || nodeType === 'memory') {
                hideMetadataNodes();
                if (detailPanel) {
                  detailPanel.textContent = 'Hover over a CHO node or click a memory node to inspect its metadata.';
                }
              }
            });
          });

          metadataNodes.forEach((node) => {
            node.addEventListener('mouseenter', function () {
              if (detailPanel) {
                detailPanel.textContent = node.getAttribute('data-details') || 'No metadata details available.';
              }
            });
            node.addEventListener('click', function (event) {
              event.preventDefault();
              if (detailPanel) {
                detailPanel.textContent = node.getAttribute('data-details') || 'No metadata details available.';
              }
            });
            node.addEventListener('mouseleave', function () {
              if (detailPanel) {
                detailPanel.textContent = 'Hover over a CHO node or click a memory node to inspect its metadata.';
              }
            });
            node.addEventListener('click', function (event) {
              event.preventDefault();
              const parentId = node.getAttribute('data-parent-id');
              const nodeType = node.getAttribute('data-node-type');
              if (nodeType === 'memory' || nodeType === 'cho') {
                showMetadataNodesFor(parentId, nodeType);
              }
              if (detailPanel) {
                detailPanel.textContent = node.getAttribute('data-details') || 'No metadata details available.';
              }
            });
          });
        }
      });
    </script>
  </body>
</html>
"""

IMPORT_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Import memory</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; background: #f4f7fb; color: #1f2937; }
      .wrap { max-width: 760px; margin: 32px auto; padding: 24px; }
      .card { background: white; border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
      form input, form textarea { width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
      button { padding: 8px 12px; border: 0; border-radius: 6px; background: #2563eb; color: white; cursor: pointer; }
      a { color: #2563eb; text-decoration: none; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>Import a new memory</h1>
        <p>Upload a text file and assign the initial memory metadata before the memory becomes available in the web app.</p>
        <a href="/">Back to dashboard</a>
      </div>
      <div class="card">
        <form action="/memories/import" method="post" enctype="multipart/form-data">
          <label>Text file</label>
          <input name="file" type="file" required>
          <label>ID</label>
          <input name="id" placeholder="e.g. 005">
          <label>Title</label>
          <input name="dc:title" placeholder="Memory title">
          <label>Creator</label>
          <input name="dc:creator" placeholder="Creator">
          <label>Date</label>
          <input name="dc:date" placeholder="Date">
          <label>Subject</label>
          <input name="dc:subject" placeholder="Subject">
          <label>Description</label>
          <textarea name="dc:description" placeholder="Description"></textarea>
          <button type="submit">Import memory</button>
        </form>
      </div>
    </div>
  </body>
</html>
"""


def _normalize_text(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
                    parts.append({
                        "type": "span",
                        "value": highlighted_value,
                        "kind": "memory" if span.get("type") == MetadataType.MEMORY.value else "cho",
                        "field": span.get("field", "")
                    })
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


def _load_context(memory_id=None, focus_cho=None):
    memories = session.query(Memory).order_by(Memory.id).all()
    chos = session.query(CHO).order_by(CHO.id).all()

    selected_memory = None
    metadata = []
    paragraphs = []
    memory_metadata_items = []
    cho_metadata_items = []

    if memory_id is not None:
        selected_memory = session.query(Memory).get(memory_id)
    elif memories:
        selected_memory = memories[0]

    if selected_memory is not None:
        metadata = extract_metadata(selected_memory.text or "")
        if not selected_memory.title:
            selected_memory.title = get_memory_title(selected_memory.text or "", "Untitled memory")

        memory_metadata_items = [
            {"field": md["field"], "value": md["value"]}
            for md in metadata
            if md.get("type") == MetadataType.MEMORY.value
        ]
        cho_metadata_items = [
            {"cho": md.get("cho"), "field": md["field"], "value": md["value"]}
            for md in metadata
            if md.get("type") == MetadataType.CHO.value and md.get("cho")
        ]
        paragraphs = _build_paragraphs(selected_memory.text or "")

    return memories, chos, selected_memory, metadata, paragraphs, memory_metadata_items, cho_metadata_items, focus_cho


def _build_graph_data(selected_memory_id=None, focus_cho=None):
    memories = session.query(Memory).order_by(Memory.id).all()
    cho_rows = session.query(CHO).order_by(CHO.id).all()
    nodes = []
    edges = []
    seen_nodes = {}
    cho_metadata_positions = {}

    def add_node(node_id, label, group, x, y, link, radius=32, parent_id="", details=""):
        if node_id not in seen_nodes:
            seen_nodes[node_id] = {"id": node_id, "label": label, "group": group, "x": x, "y": y, "link": link, "radius": radius, "parent_id": parent_id, "details": details}
            nodes.append(seen_nodes[node_id])
        return seen_nodes[node_id]

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
            metadata_items = extract_metadata(memory.text or "")
            if matches_cho(metadata_items, focus_cho):
                relevant_memories.append(memory)
        memories = relevant_memories
        cho_rows = [target_cho] if target_cho is not None else []
    elif selected_memory_id is not None:
        selected_memory = session.query(Memory).get(selected_memory_id)
        memories = [selected_memory] if selected_memory is not None else []
        cho_rows = []
        if selected_memory is not None:
            for md in extract_metadata(selected_memory.text or ""):
                if md.get("type") == MetadataType.CHO.value and md.get("cho"):
                    cho_id = md.get("cho")
                    cho = next((item for item in session.query(CHO).order_by(CHO.id).all() if str(item.custom_id) == str(cho_id) or str(item.id) == str(cho_id)), None)
                    if cho is not None:
                        cho_rows.append(cho)
        cho_rows = list(dict.fromkeys(cho_rows))

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
            f"Memory {memory.id}",
        )

        metadata_items = extract_metadata(memory.text or "")
        for md_index, md in enumerate(metadata_items):
            if md.get("type") == MetadataType.MEMORY.value:
                continue  # skip memory metadata entirely
                md_label = md.get("field") or "metadata"
                md_node = add_node(
                    f"memory_md:{memory.id}:{md_index}:{md_label}",
                    md_label,
                    "memory_metadata",
                    420,
                    140 + index * 180 + md_index * 70,
                    memory_link,
                    24,
                    f"memory:{memory.id}",
                    f"{md_label}: {md.get('value', '')}",
                )
                edges.append((memory_node, md_node))
            elif md.get("type") == MetadataType.CHO.value and md.get("cho"):
                cho_id = md.get("cho")
                cho = next((item for item in cho_rows if str(item.custom_id) == str(cho_id) or str(item.id) == str(cho_id)), None)
                if cho is None:
                    continue
                cho_index = cho_rows.index(cho)
                cho_link = f"/?memory_id={selected_memory_id or ''}&focus_cho={cho.custom_id or cho.id}" if selected_memory_id is not None else f"/?focus_cho={cho.custom_id or cho.id}"
                cho_node = add_node(
                    f"cho:{cho.custom_id or cho.id}",
                    cho.title or cho.custom_id or str(cho.id),
                    "cho",
                    760,
                    140 + cho_index * 220,
                    cho_link,
                    36,
                    "",
                    f"{cho.title or cho.custom_id or str(cho.id)}: {md.get('field', '')} = {md.get('value', '')}",
                )
                metadata_label = md.get("field") or "metadata"
                cho_key = str(cho.custom_id or cho.id)
                position_key = (cho_key, metadata_label, str(md.get("value", "")))
                cho_column_positions = cho_metadata_positions.setdefault(cho_key, {})
                metadata_row = cho_column_positions.setdefault(position_key, len(cho_column_positions))
                metadata_node = add_node(
                    f"cho_md:{cho.custom_id or cho.id}:{memory.id}:{metadata_label}:{md_index}",
                    metadata_label,
                    "cho_metadata",
                    600,
                    140 + cho_index * 220 + metadata_row * 70,
                    cho_link,
                    24,
                    f"cho:{cho.custom_id or cho.id}",
                    f"{metadata_label}: {md.get('value', '')}",
                )
                edges.extend([(memory_node, metadata_node), (metadata_node, cho_node)])

    return nodes, edges


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


def _append_metadata_tag(text, field, value, metadata_type, cho=None):
    if not value:
        return text
    tag = f'<{field} type="memory">{value}</{field}>' if metadata_type == MetadataType.MEMORY.value else f'<{field} cho="{cho}">{value}</{field}>'
    separator = "\n" if text and not text.endswith("\n") else ""
    return f"{text}{separator}{tag}"


def create_app(testing=False):
    app = Flask(__name__)
    app.config["TESTING"] = testing

    @app.route("/")
    def index():
        memory_id = request.args.get("memory_id", type=int)
        focus_cho = request.args.get("focus_cho", "")
        memories, chos, selected_memory, metadata, paragraphs, memory_metadata_items, cho_metadata_items, _ = _load_context(memory_id, focus_cho)
        nodes, edges = _build_graph_data(memory_id, focus_cho)
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
            nodes=nodes,
            edges=edges,
            focus_cho=focus_cho,
            focus_memory=f"memory:{memory_id}" if memory_id else "",
        )

    @app.route("/memories/import", methods=["GET", "POST"])
    def import_memory():
        if request.method == "POST":
            uploaded = request.files.get("file")
            if not uploaded or not uploaded.filename:
                return redirect(url_for("import_memory"))

            mid = request.form.get("id", "").strip() or str(uuid.uuid4())[:8]
            metadata = {}
            for field in ("dc:title", "dc:creator", "dc:date", "dc:subject", "dc:description"):
                value = request.form.get(field, "").strip()
                if value:
                    metadata[field] = value

            with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
                uploaded.save(handle.name)
                temp_path = handle.name

            try:
                new_path = copy_memory_file(temp_path, mid)
                with open(temp_path, encoding="utf-8", errors="replace") as handle:
                    txt = handle.read()
                txt = html.unescape(txt)
                txt = re.sub(r"<rdf:RDF.*?</rdf:RDF>", "", txt, flags=re.DOTALL)
                final_text = rebuild_memory_text(txt, metadata)
                memory = Memory(custom_id=mid, title=metadata.get("dc:title", mid), text=final_text, file_path=new_path)
                session.add(memory)
                session.commit()
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            return redirect(url_for("index", memory_id=memory.id))

        return render_template_string(IMPORT_TEMPLATE)

    @app.route("/memories/<int:memory_id>/edit", methods=["POST"])
    def edit_memory(memory_id):
        memory = session.query(Memory).get(memory_id)
        if memory is not None:
            memory.title = request.form.get("title", "").strip() or (memory.title or f"Memory {memory.id}")
            updated_text = request.form.get("text", "")

            for key in request.form:
                if key.startswith("delete_memory_metadata[") and key.endswith("]"):
                    field = key[len("delete_memory_metadata["):-1]
                    updated_text = _remove_metadata_tag(updated_text, field, MetadataType.MEMORY.value)
                elif key.startswith("delete_cho_metadata[") and "]" in key:
                    remainder = key[len("delete_cho_metadata["):]
                    cho_id, field = remainder.split("][")
                    field = field[:-1]
                    updated_text = _remove_metadata_tag(updated_text, field, MetadataType.CHO.value, cho=cho_id)
                elif key == "delete_memory_metadata" and request.form.get(key):
                    updated_text = _remove_metadata_tag(updated_text, request.form.get(key), MetadataType.MEMORY.value)
                elif key == "delete_cho_metadata" and request.form.get(key):
                    updated_text = _remove_metadata_tag(updated_text, request.form.get(key), MetadataType.CHO.value)

            for key, value in request.form.items():
                if key.startswith("memory_metadata[") and key.endswith("]"):
                    field = key[len("memory_metadata["):-1]
                    updated_text = _replace_metadata_tag(updated_text, field, value, MetadataType.MEMORY.value)
                elif key.startswith("cho_metadata[") and "]" in key:
                    remainder = key[len("cho_metadata["):]
                    cho_id, field = remainder.split("][")
                    field = field[:-1]
                    updated_text = _replace_metadata_tag(updated_text, field, value, MetadataType.CHO.value, cho=cho_id)

            if request.form.get("add_memory_metadata") and request.form.get("new_memory_metadata_field"):
                updated_text = _append_metadata_tag(
                    updated_text,
                    request.form.get("new_memory_metadata_field", "").strip(),
                    request.form.get("new_memory_metadata_value", "").strip(),
                    MetadataType.MEMORY.value,
                )

            if request.form.get("add_cho_metadata") and request.form.get("new_cho_metadata_field"):
                updated_text = _append_metadata_tag(
                    updated_text,
                    request.form.get("new_cho_metadata_field", "").strip(),
                    request.form.get("new_cho_metadata_value", "").strip(),
                    MetadataType.CHO.value,
                    cho=request.form.get("new_cho_metadata_cho", "").strip(),
                )

            memory.text = updated_text
            session.add(memory)
            session.commit()
        return redirect(url_for("index", memory_id=memory_id))

    @app.route("/memories/<int:memory_id>/annotate", methods=["POST"])
    def annotate_memory(memory_id):
        memory = session.query(Memory).get(memory_id)
        if memory is not None:
            annotation_text = request.form.get("selected_annotation_text", "").strip() or request.form.get("annotation_text", "").strip()
            annotation_field = request.form.get("annotation_field", "").strip()
            annotation_cho = request.form.get("annotation_cho", "").strip()
            if annotation_text and annotation_field and annotation_cho:
                annotation = f'<{annotation_field} cho="{annotation_cho}">{annotation_text}</{annotation_field}>'
                current_text = memory.text or ""
                if annotation_text in current_text:
                    memory.text = current_text.replace(annotation_text, annotation, 1)
                else:
                    memory.text = current_text + ("\n" if current_text else "") + annotation
                session.add(memory)
                session.commit()
        return redirect(url_for("index", memory_id=memory_id))

    @app.route("/graph")
    def graph():
        memory_id = request.args.get("memory_id", type=int)
        focus_cho = request.args.get("focus_cho", "")
        memories, chos, selected_memory, metadata, paragraphs, memory_metadata_items, cho_metadata_items, _ = _load_context(memory_id, focus_cho)
        nodes, edges = _build_graph_data(memory_id, focus_cho)
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
            nodes=nodes,
            edges=edges,
            focus_cho=focus_cho,
            focus_memory=f"memory:{memory_id}" if memory_id else "",
        )

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
