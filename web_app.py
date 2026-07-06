import html
import os
import re
import tempfile
import uuid
import xml.etree.ElementTree as ET

from flask import Flask, Response, redirect, render_template_string, request, url_for

from config import APP_DATA_DIR
from db import CHO, Memory, session
from services.memory_service import rebuild_memory_text
from services.metadata import extract_metadata, get_memory_title, parse_text_and_spans
from services.metadata_schema import METADATA_FIELDS
from services.types import MetadataType


CHO_FIELDS = [
    {"field": field, "label": meta.get("label", field)}
    for category in ("CHO", "Agent")
    for field, meta in METADATA_FIELDS.get(category, {}).get("fields", {}).items()
]

SEARCH_PAGE_SIZE = 10
IMPORT_FIELDS = ("dc:title", "dc:creator", "dc:date", "dc:subject", "dc:description")

MEMORY_FIELDS = [
    {"field": field, "label": field.split(":")[-1].replace("_", " ").title()}
    for field in IMPORT_FIELDS
]


HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CORDHISK Web</title>
    <style>
      :root {
        --bg: #eef3fb;
        --ink: #1f2937;
        --brand: #1d4ed8;
        --brand-2: #0ea5e9;
        --surface: #ffffff;
        --line: #dbe4f0;
        --shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
      }
      body { font-family: "Avenir Next", "Segoe UI", sans-serif; margin: 0; background: radial-gradient(circle at 10% 10%, #f8fbff 0%, var(--bg) 52%, #e4edf9 100%); color: var(--ink); }
      .shell { display: grid; grid-template-columns: 300px 1fr; min-height: 100vh; }
      .sidebar { background: linear-gradient(180deg, #0f172a 0%, #16213b 100%); color: white; padding: 20px; }
      .content { padding: 24px; }
      .card { background: var(--surface); border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: var(--shadow); border: 1px solid rgba(219, 228, 240, 0.7); }
      a { color: #2563eb; text-decoration: none; }
      .pill { display: inline-flex; align-items: center; margin: 3px; padding: 5px 10px; border-radius: 999px; background: #e2e8f0; font-size: 12px; border: 1px solid transparent; }
      .pill.memory { background: #dbeafe; color: #1d4ed8; border-color: #bfdbfe; }
      .pill.cho { background: #dcfce7; color: #166534; border-color: #86efac; }
      .pill.add { background: #2563eb; color: white; border-color: #1d4ed8; cursor: pointer; font-weight: 700; min-width: 28px; justify-content: center; }
      .pill.selected { box-shadow: 0 0 0 2px #0f172a inset; }
      .text-view { font-family: inherit; line-height: 1.7; white-space: normal; }
      .text-view p { margin: 0 0 10px; }
      form input, form select, form textarea { width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
      form textarea { min-height: 140px; }
      button { padding: 8px 12px; border: 0; border-radius: 8px; background: var(--brand); color: white; cursor: pointer; transition: transform 0.08s ease, opacity 0.12s ease; }
      button:hover { opacity: 0.96; }
      button:active { transform: translateY(1px); }
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
      .graph-hover-value { min-height: 32px; display: flex; align-items: center; padding: 6px 10px; border: 1px solid #dbe4f0; border-radius: 8px; background: #f8fafc; color: #334155; font-size: 13px; min-width: 280px; }
      .grid { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.95fr); gap: 16px; }
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
      .result-table { width: 100%; border-collapse: collapse; font-size: 14px; }
      .result-table th, .result-table td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #e5e7eb; }
      .inline-form { display: flex; gap: 8px; align-items: end; flex-wrap: wrap; margin-top: 10px; }
      .inline-form > div { min-width: 160px; }
      .inline-form label { display: block; font-size: 12px; margin-bottom: 3px; }
      .notice { padding: 10px 12px; border-radius: 8px; margin-bottom: 14px; font-size: 14px; }
      .notice.success { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
      .notice.error { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
      .cta-btn { display: inline-block; padding: 9px 13px; border-radius: 6px; background: #0ea5e9; color: white; text-decoration: none; }
      .tag-section { margin: 14px 0 18px; }
      .tag-section h4 { margin: 0 0 8px; }
      .tag-help { color: #475569; font-size: 13px; margin: 0 0 8px; }
      .tag-list { display: flex; flex-wrap: wrap; gap: 6px; }
      .tag-selector { display: inline-flex; align-items: center; cursor: pointer; }
      .tag-selector input { position: absolute; opacity: 0; pointer-events: none; }
      .tag-selector.empty { cursor: default; }
      .compact-tools { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
      .compact-tools .metadata-section h5 { margin-top: 0; }
      .cho-memory-group { margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #eef2f7; }
      .cho-memory-group:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: 0; }
      .meta-toggle { display: flex; gap: 8px; margin: 10px 0 12px; flex-wrap: wrap; }
      .meta-toggle a { display: inline-block; padding: 6px 10px; border-radius: 999px; font-size: 12px; border: 1px solid #bfdbfe; color: #1e3a8a; background: #eff6ff; }
      .meta-toggle a.active { color: white; background: #1d4ed8; border-color: #1d4ed8; }
      .metadata-card { position: sticky; top: 12px; }
      .metadata-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
      .metadata-inline-edit { display: none; margin-top: 10px; padding: 10px; border: 1px solid #dbeafe; border-radius: 8px; background: #f0f7ff; }
      .memory-mode-hide { display: none; }
      .sidebar-list { list-style: none; margin: 0; padding: 0; }
      .sidebar-list li { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
      .sidebar-list a { color: #0f172a; display: inline-block; max-width: 210px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .mini-delete { width: 24px; min-width: 24px; height: 24px; line-height: 24px; padding: 0; border-radius: 999px; background: #ef4444; color: white; font-weight: 700; font-size: 14px; }
      .sidebar-action { margin-bottom: 12px; }
      .sidebar-action button { width: 100%; background: #0ea5e9; }
      .sidebar-pop { display: none; margin-top: 8px; padding: 10px; border-radius: 8px; background: rgba(15, 23, 42, 0.45); border: 1px solid rgba(148, 163, 184, 0.4); }
      .sidebar-pop label { font-size: 12px; color: #bfdbfe; display: block; margin-bottom: 2px; }
      .sidebar-pop input, .sidebar-pop select { margin-bottom: 8px; }
      .sidebar-card { background: #f8fbff; }
      .sidebar-card h3 { color: #0f172a; }
      .sidebar-button-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
      .side-btn, .side-btn:visited { display: inline-flex; align-items: center; justify-content: center; text-align: center; min-height: 34px; padding: 6px; border-radius: 8px; color: white; background: #0ea5e9; border: 0; font-size: 12px; font-weight: 600; }
      .side-btn.alt { background: #1d4ed8; }
      .side-btn.disabled { pointer-events: none; opacity: 0.6; }
      .inline-annotation-row { display: grid; grid-template-columns: minmax(260px, 2fr) minmax(170px, 1fr) minmax(170px, 1fr) auto; gap: 8px; align-items: end; }
      .inline-annotation-row > div { min-width: 0; }
      .inline-annotation-row label { display: block; font-size: 12px; margin-bottom: 3px; }
      .inline-annotation-row input, .inline-annotation-row select { margin-bottom: 0; }
      .inline-annotation-row button { white-space: nowrap; }
      @media (max-width: 980px) {
        .shell { grid-template-columns: 1fr; }
        .sidebar { border-bottom: 1px solid #334155; }
        .grid { grid-template-columns: 1fr; }
        .metadata-card { position: static; }
        .sidebar-button-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .inline-annotation-row { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <aside class="sidebar">
        <h2>CORDHISK</h2>
        <p>Web-based metadata workspace for memories and cultural heritage objects.</p>
        <div class="sidebar-button-grid">
          <a class="side-btn" href="/memories/import">Import TXT memory</a>
          <a class="side-btn" href="/search">Search</a>
          <a class="side-btn" href="/compare">Compare</a>
          <button type="button" class="side-btn alt" id="open-add-cho">Add CHO</button>
          <button type="button" class="side-btn alt" id="open-export-cho">Download CHO RDF</button>
          {% if selected_memory %}
          <a class="side-btn alt" href="/export/memory/{{ selected_memory.id }}.rdf">Download Memory RDF</a>
          {% else %}
          <span class="side-btn alt disabled">Download Memory RDF</span>
          {% endif %}
        </div>
        <div class="sidebar-action">
          <form id="add-cho-pop" class="sidebar-pop" action="/chos/create" method="post">
            <label>CHO code</label>
            <input name="custom_id" placeholder="e.g. PR99" required>
            <label>Title</label>
            <input name="title" placeholder="CHO title">
            {% if selected_memory %}
            <input type="hidden" name="memory_id" value="{{ selected_memory.id }}">
            {% endif %}
            <button type="submit">Create CHO</button>
          </form>
        </div>
        <div class="sidebar-action">
          <form id="export-cho-pop" class="sidebar-pop" action="/export/cho" method="get">
            <label>CHO</label>
            <select name="cho_id" required>
              {% for cho in chos %}
              <option value="{{ cho.custom_id or cho.id }}">{{ cho.title or cho.custom_id or cho.id }}</option>
              {% endfor %}
            </select>
            <label>Mode</label>
            <select name="mode">
              <option value="single">Single memory</option>
              <option value="all">All memories</option>
            </select>
            {% if selected_memory %}
            <input type="hidden" name="memory_id" value="{{ selected_memory.id }}">
            {% endif %}
            <button type="submit">Download</button>
          </form>
        </div>
        <div class="card sidebar-card">
          <h3>Memories</h3>
          <ul class="sidebar-list">
            {% for memory in memories %}
            <li>
              <a href="/?memory_id={{ memory.id }}{% if focus_cho %}&focus_cho={{ focus_cho }}{% endif %}&meta_view={{ active_meta_view }}">{{ memory.custom_id or memory.id }} — {{ memory.title or ('Memory ' ~ memory.id) }}</a>
              <form action="/memories/{{ memory.id }}/delete" method="post" onsubmit="return confirm('Delete this memory permanently?');">
                <button type="submit" class="mini-delete" title="Delete memory">-</button>
              </form>
            </li>
            {% endfor %}
          </ul>
        </div>
        <div class="card sidebar-card">
          <h3>CHO records</h3>
          <ul class="sidebar-list">
            {% for cho in chos %}
            <li>
              <a href="/?memory_id={{ selected_memory.id if selected_memory else '' }}&focus_cho={{ cho.custom_id or cho.id }}&meta_view=cho">{{ cho.custom_id or cho.id }} — {{ cho.title or cho.custom_id or cho.id }}</a>
              <form action="/chos/{{ cho.id }}/delete{% if selected_memory %}?memory_id={{ selected_memory.id }}{% endif %}" method="post" onsubmit="return confirm('Delete this CHO and remove its tags from all memories?');">
                <button type="submit" class="mini-delete" title="Delete CHO">-</button>
              </form>
            </li>
            {% endfor %}
          </ul>
        </div>
      </aside>
      <main class="content">
        {% if notice_message %}
        <div class="notice {{ notice_level }}">{{ notice_message }}</div>
        {% endif %}
        {% if selected_memory %}
        <div class="grid">
          <div class="card">
            <h2>{{ selected_memory.custom_id or selected_memory.id }} — {{ selected_memory.title or ('Memory ' ~ selected_memory.id) }}</h2>
            {% if active_meta_view == 'memory' %}
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
              <div class="inline-annotation-row">
                <div>
                  <label>Selected text</label>
                  <input id="selected-annotation-text" name="selected_annotation_text" placeholder="Selected text">
                </div>
                <div>
                  <label>CHO</label>
                  <select name="annotation_cho">
                    {% for cho in chos %}
                    <option value="{{ cho.custom_id or cho.id }}">{{ cho.title or cho.custom_id or cho.id }}</option>
                    {% endfor %}
                  </select>
                </div>
                <div>
                  <label>Field</label>
                  <select name="annotation_field">
                    {% for field in cho_fields %}
                    <option value="{{ field.field }}">{{ field.label }}</option>
                    {% endfor %}
                  </select>
                </div>
                <div>
                  <button type="submit">Add annotation</button>
                </div>
              </div>
              <input type="hidden" name="focus_cho" value="{{ focus_cho or '' }}">
              <input type="hidden" name="meta_view" value="{{ active_meta_view }}">
            </form>
            {% else %}
            <div class="notice success">
              CHO metadata view is active. Switch to Memory metadata to inspect or annotate full memory content.
            </div>
            {% endif %}
            <div class="card graph-card" style="margin-top: 14px;">
              <h3>Memory relationship graph</h3>
              <p>Click a memory node to reveal its metadata and hover a CHO node to inspect its metadata.</p>
              <div class="graph-toolbar">
                <button type="button" id="zoom-in">Zoom in</button>
                <button type="button" id="zoom-out">Zoom out</button>
                <button type="button" id="reset-view">Reset view</button>
                <div id="graph-hover-value" class="graph-hover-value">Hover CHO or metadata nodes to inspect values.</div>
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
            </div>
          </div>
          <div>
            <div class="card metadata-card">
              <h3>Metadata Panel</h3>
              <p>Switch between Memory and CHO metadata visualisations without leaving this memory context.</p>
              <div class="meta-toggle">
                <a href="/?memory_id={{ selected_memory.id }}{% if focus_cho %}&focus_cho={{ focus_cho }}{% endif %}&meta_view=memory" class="{% if active_meta_view == 'memory' %}active{% endif %}">Memory metadata</a>
                <a href="/?memory_id={{ selected_memory.id }}{% if focus_cho %}&focus_cho={{ focus_cho }}{% endif %}&meta_view=cho" class="{% if active_meta_view == 'cho' %}active{% endif %}">CHO metadata</a>
              </div>

              {% if active_meta_view == 'cho' and selected_cho_details %}
                <h4>CHO {{ selected_cho_details.label }} — {{ selected_cho_details.title }}</h4>
                <p>Metadata grouped by memory for the selected CHO.</p>
                {% for group in selected_cho_details.memories %}
                <div class="cho-memory-group">
                  <p><strong><a href="/?memory_id={{ group.memory_id }}&focus_cho={{ selected_cho_details.label }}&meta_view=cho">{{ group.memory_label }}</a></strong></p>
                  <div class="tag-list">
                    {% for tag in group.tags %}
                    <span class="pill cho">{{ tag.field }}: {{ tag.value }}</span>
                    {% endfor %}
                  </div>
                </div>
                {% else %}
                <p>No metadata found for this CHO in the current memories.</p>
                {% endfor %}
              {% elif active_meta_view == 'cho' %}
                <p>Select a CHO from the sidebar or graph to view CHO metadata grouped by memory.</p>
              {% else %}
                <form action="/memories/{{ selected_memory.id }}/edit" method="post" id="memory-metadata-form">
                  <input type="hidden" name="focus_cho" value="{{ focus_cho or '' }}">
                  <input type="hidden" name="meta_view" value="memory">
                  <input type="hidden" id="inline-edit-field" name="edit_memory_metadata_field" value="">
                  <input type="hidden" id="inline-edit-value" name="edit_memory_metadata_value" value="">

                  <div class="tag-section">
                    <h4>Memory tags</h4>
                    <p class="tag-help">Double-click a memory tag to update its value. Use checkboxes and remove selected tags.</p>
                    <div class="tag-list">
                      {% for md in memory_metadata_items %}
                      <label class="tag-selector">
                        <input type="checkbox" name="delete_memory_metadata[{{ md.field }}]" value="1">
                        <span class="pill memory memory-editable" data-memory-field="{{ md.field }}" data-memory-value="{{ md.value }}">{{ md.field }}: {{ md.value }}</span>
                      </label>
                      {% else %}
                      <span class="pill memory">No memory metadata</span>
                      {% endfor %}
                      <button type="button" class="pill add" id="open-add-memory-tag" title="Add memory metadata">+</button>
                    </div>
                  </div>

                  <div id="add-memory-tag-box" class="metadata-inline-edit">
                    <label>Field</label>
                    <select name="new_memory_metadata_field">
                      {% for field in memory_fields %}
                      <option value="{{ field.field }}">{{ field.label }} ({{ field.field }})</option>
                      {% endfor %}
                    </select>
                    <label>Value</label>
                    <input name="new_memory_metadata_value" placeholder="New value">
                  </div>

                  <div class="tag-section">
                    <h4>CHO tags in this memory</h4>
                    <div class="tag-list">
                      {% for md in cho_metadata_items %}
                      <label class="tag-selector">
                        <input type="checkbox" name="delete_cho_metadata[{{ md.cho }}][{{ md.field }}]" value="1">
                        <span class="pill cho">{{ md.cho }} / {{ md.field }}: {{ md.value }}</span>
                      </label>
                      {% else %}
                      <span class="pill cho">No CHO metadata</span>
                      {% endfor %}
                    </div>
                  </div>

                  <div class="metadata-actions">
                    <button type="submit">Save metadata changes</button>
                    <button type="submit" name="remove_selected" value="1">Remove selected tags</button>
                  </div>
                </form>
              {% endif %}
            </div>
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
        const hoverValueBox = document.getElementById('graph-hover-value');
        const zoomInButton = document.getElementById('zoom-in');
        const zoomOutButton = document.getElementById('zoom-out');
        const resetButton = document.getElementById('reset-view');
        const addMemoryTagButton = document.getElementById('open-add-memory-tag');
        const addMemoryTagBox = document.getElementById('add-memory-tag-box');
        const memoryMetadataForm = document.getElementById('memory-metadata-form');
        const inlineEditField = document.getElementById('inline-edit-field');
        const inlineEditValue = document.getElementById('inline-edit-value');
        const openAddCho = document.getElementById('open-add-cho');
        const addChoPop = document.getElementById('add-cho-pop');
        const openExportCho = document.getElementById('open-export-cho');
        const exportChoPop = document.getElementById('export-cho-pop');
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

        document.querySelectorAll('.tag-selector input').forEach(function (input) {
          const label = input.closest('.tag-selector');
          const pill = label ? label.querySelector('.pill') : null;
          const syncSelectedState = function () {
            if (pill) {
              pill.classList.toggle('selected', input.checked);
            }
          };
          input.addEventListener('change', syncSelectedState);
          syncSelectedState();
        });

        document.querySelectorAll('.memory-editable').forEach(function (pill) {
          pill.addEventListener('dblclick', function () {
            if (!memoryMetadataForm || !inlineEditField || !inlineEditValue) {
              return;
            }
            const field = pill.getAttribute('data-memory-field') || '';
            const currentValue = pill.getAttribute('data-memory-value') || '';
            if (!field) {
              return;
            }
            const updated = window.prompt('Update value for ' + field, currentValue);
            if (updated === null) {
              return;
            }
            const trimmed = updated.trim();
            if (!trimmed) {
              return;
            }
            inlineEditField.value = field;
            inlineEditValue.value = trimmed;
            memoryMetadataForm.submit();
          });
        });

        if (addMemoryTagButton && addMemoryTagBox) {
          addMemoryTagButton.addEventListener('click', function () {
            const isVisible = addMemoryTagBox.style.display === 'block';
            addMemoryTagBox.style.display = isVisible ? 'none' : 'block';
          });
        }

        if (openAddCho && addChoPop) {
          openAddCho.addEventListener('click', function () {
            const open = addChoPop.style.display === 'block';
            addChoPop.style.display = open ? 'none' : 'block';
          });
        }

        if (openExportCho && exportChoPop) {
          openExportCho.addEventListener('click', function () {
            const open = exportChoPop.style.display === 'block';
            exportChoPop.style.display = open ? 'none' : 'block';
          });
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
          let hideTimer = null;
          const setHoverValue = (text) => {
            if (hoverValueBox) {
              hoverValueBox.textContent = text || 'No metadata details available.';
            }
          };
          const cancelHideTimer = () => {
            if (hideTimer) {
              clearTimeout(hideTimer);
              hideTimer = null;
            }
          };
          const scheduleHideMetadataNodes = () => {
            cancelHideTimer();
            hideTimer = setTimeout(() => {
              hideMetadataNodes();
            }, 120);
          };
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
              cancelHideTimer();
              const parentId = node.getAttribute('data-parent-id');
              const nodeType = node.getAttribute('data-node-type');
              if (nodeType === 'cho' || nodeType === 'memory') {
                showMetadataNodesFor(parentId, nodeType);
              }
              setHoverValue(node.getAttribute('data-details'));
            });
            node.addEventListener('mouseleave', function () {
              const nodeType = node.getAttribute('data-node-type');
              if (nodeType === 'cho') {
                scheduleHideMetadataNodes();
              }
            });
            node.addEventListener('click', function (event) {
              const nodeType = node.getAttribute('data-node-type');
              if (nodeType === 'cho' || nodeType === 'memory') {
                const parentId = node.getAttribute('data-parent-id');
                showMetadataNodesFor(parentId, nodeType);
                setHoverValue(node.getAttribute('data-details'));
              }
            });
          });

          metadataNodes.forEach((node) => {
            node.addEventListener('mouseenter', function () {
              cancelHideTimer();
              setHoverValue(node.getAttribute('data-details'));
            });
            node.addEventListener('click', function (event) {
              event.preventDefault();
              setHoverValue(node.getAttribute('data-details'));
            });
            node.addEventListener('mouseleave', function () {
              scheduleHideMetadataNodes();
            });
          });
        }
      });
    </script>
  </body>
</html>
"""

SEARCH_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Search memories</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; background: #f4f7fb; color: #1f2937; }
      .wrap { max-width: 980px; margin: 32px auto; padding: 24px; }
      .card { background: white; border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
      form input { width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
      button { padding: 8px 12px; border: 0; border-radius: 6px; background: #2563eb; color: white; cursor: pointer; }
      a { color: #2563eb; text-decoration: none; }
      table { width: 100%; border-collapse: collapse; }
      th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #e5e7eb; }
      .snippet { color: #475569; }
      .pagination { margin-top: 10px; display: flex; gap: 12px; align-items: center; }
      .back-btn { display: inline-block; padding: 8px 12px; border-radius: 6px; background: #1d4ed8; color: white; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>Search memories</h1>
        <p>This mirrors the desktop search flow across memory text.</p>
        <a class="back-btn" href="/">Back to main page</a>
      </div>
      <div class="card">
        <form method="get" action="/search">
          <label>Search term</label>
          <input name="q" value="{{ q }}" placeholder="Type a word or phrase">
          <button type="submit">Search</button>
        </form>
      </div>
      {% if searched %}
      <div class="card">
        <h2>Results ({{ total_results }})</h2>
        <table>
          <thead><tr><th>Memory</th><th>Title</th><th>Snippet</th></tr></thead>
          <tbody>
            {% for row in result_rows %}
            <tr>
              <td><a href="/?memory_id={{ row.id }}">{{ row.custom_id or row.id }}</a></td>
              <td>{{ row.title or ('Memory ' ~ row.id) }}</td>
              <td class="snippet">{{ row.snippet }}</td>
            </tr>
            {% else %}
            <tr><td colspan="3">No matches found.</td></tr>
            {% endfor %}
          </tbody>
        </table>
        {% if total_pages > 1 %}
        <div class="pagination">
          {% if page > 1 %}
          <a href="/search?q={{ q }}&page={{ page - 1 }}">Previous</a>
          {% endif %}
          <span>Page {{ page }} of {{ total_pages }}</span>
          {% if page < total_pages %}
          <a href="/search?q={{ q }}&page={{ page + 1 }}">Next</a>
          {% endif %}
        </div>
        {% endif %}
      </div>
      {% endif %}
    </div>
  </body>
</html>
"""

COMPARE_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Compare CHO metadata</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; background: #f4f7fb; color: #1f2937; }
      .wrap { max-width: 980px; margin: 32px auto; padding: 24px; }
      .card { background: white; border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
      form select { width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
      button { padding: 8px 12px; border: 0; border-radius: 6px; background: #2563eb; color: white; cursor: pointer; }
      a { color: #2563eb; text-decoration: none; }
      table { width: 100%; border-collapse: collapse; }
      th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #e5e7eb; }
      .matrix th:first-child, .matrix td:first-child { min-width: 170px; font-weight: 600; background: #f8fafc; }
      .matrix-wrap { overflow: auto; }
      .back-btn { display: inline-block; padding: 8px 12px; border-radius: 6px; background: #1d4ed8; color: white; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>Compare by CHO</h1>
        <p>Compare metadata fields across memories for one CHO, with each memory shown as a column.</p>
        <a class="back-btn" href="/">Back to main page</a>
      </div>
      <div class="card">
        <form method="get" action="/compare">
          <label>CHO</label>
          <select name="cho_id">
            <option value="">Choose CHO</option>
            {% for cho in chos %}
            <option value="{{ cho.custom_id or cho.id }}" {% if selected_cho == (cho.custom_id or cho.id|string) %}selected{% endif %}>{{ cho.title or cho.custom_id or cho.id }}</option>
            {% endfor %}
          </select>
          <button type="submit">Compare</button>
        </form>
      </div>
      {% if selected_cho %}
      <div class="card">
        <h2>Results for CHO {{ selected_cho }}</h2>
        <div class="matrix-wrap">
          <table class="matrix">
            <thead>
              <tr>
                <th>Field</th>
                {% for memory in memory_columns %}
                <th><a href="/?memory_id={{ memory.id }}&focus_cho={{ selected_cho }}&meta_view=cho">{{ memory.label }}</a></th>
                {% endfor %}
              </tr>
            </thead>
            <tbody>
              {% for row in matrix_rows %}
              <tr>
                <td>{{ row.field }}</td>
                {% for memory in memory_columns %}
                <td>{{ row['values'].get(memory.id, '—') }}</td>
                {% endfor %}
              </tr>
              {% else %}
              <tr><td colspan="{{ (memory_columns|length) + 1 }}">No metadata found for this CHO.</td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
      {% endif %}
    </div>
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
      .notice { padding: 10px 12px; border-radius: 8px; margin-bottom: 14px; font-size: 14px; }
      .notice.success { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
      .notice.error { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
    </style>
  </head>
  <body>
    <div class="wrap">
      {% if notice_message %}
      <div class="notice {{ notice_level }}">{{ notice_message }}</div>
      {% endif %}
      <div class="card">
        <h1>Import a new memory</h1>
        <p>Upload a text file and assign the initial memory metadata before the memory becomes available in the web app.</p>
        <a href="/">Back to dashboard</a>
      </div>
      <div class="card">
        <form action="/memories/import" method="post" enctype="multipart/form-data">
          {% if not import_ready %}
          <input type="hidden" name="stage" value="prepare">
          <label>Text file</label>
          <input name="file" type="file" accept=".txt,text/plain" required>
          <label>ID (optional)</label>
          <input name="id" value="{{ suggested_id or '' }}" placeholder="e.g. 005">
          <button type="submit">Load metadata</button>
          {% else %}
          <input type="hidden" name="stage" value="confirm">
          <input type="hidden" name="temp_path" value="{{ temp_path }}">
          <p><strong>Detected metadata:</strong> {{ detected_count }} existing fields</p>
          <label>ID</label>
          <input name="id" value="{{ suggested_id or '' }}" placeholder="e.g. 005" required>
          <label>Title</label>
          <input name="dc:title" value="{{ form_metadata.get('dc:title', '') }}" placeholder="Memory title">
          <label>Creator</label>
          <input name="dc:creator" value="{{ form_metadata.get('dc:creator', '') }}" placeholder="Creator">
          <label>Date</label>
          <input name="dc:date" value="{{ form_metadata.get('dc:date', '') }}" placeholder="Date">
          <label>Subject</label>
          <input name="dc:subject" value="{{ form_metadata.get('dc:subject', '') }}" placeholder="Subject">
          <label>Description</label>
          <textarea name="dc:description" placeholder="Description">{{ form_metadata.get('dc:description', '') }}</textarea>
          <button type="submit">Import memory</button>
          {% endif %}
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
            if md.get("type") == MetadataType.MEMORY.value
        ]
        cho_metadata_items = [
            {"cho": md.get("cho"), "field": md["field"], "value": md["value"]}
            for md in metadata
            if md.get("type") == MetadataType.CHO.value and md.get("cho")
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
      selected_memory = session.get(Memory, selected_memory_id)
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


def _build_selected_cho_details(focus_cho):
    cho = _find_cho(focus_cho)
    if cho is None:
        return None

    cho_refs = {str(cho.id)}
    if cho.custom_id:
        cho_refs.add(str(cho.custom_id))

    memories = []
    for memory in session.query(Memory).order_by(Memory.id):
        tags = []
        for md in extract_metadata(memory.text or ""):
            if md.get("type") == MetadataType.CHO.value and str(md.get("cho")) in cho_refs:
                tags.append({
                    "field": md.get("field", ""),
                    "value": md.get("value", ""),
                })
        if tags:
            memories.append({
                "memory_id": memory.id,
                "memory_label": memory.title or memory.custom_id or f"Memory {memory.id}",
                "tags": tags,
            })

    return {
        "id": cho.id,
        "label": cho.custom_id or str(cho.id),
        "title": cho.title or cho.custom_id or str(cho.id),
        "memories": memories,
    }


def _resolve_meta_view(meta_view, focus_cho):
    requested = (meta_view or "").strip().lower()
    if requested in {"memory", "cho"}:
        return requested
    return "cho" if focus_cho else "memory"


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


def _append_metadata_tag(text, field, value, metadata_type, cho=None):
    if not value:
        return text
    tag = f'<{field} type="memory">{value}</{field}>' if metadata_type == MetadataType.MEMORY.value else f'<{field} cho="{cho}">{value}</{field}>'
    separator = "\n" if text and not text.endswith("\n") else ""
    return f"{text}{separator}{tag}"


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
    active_meta_view = _resolve_meta_view(request.args.get("meta_view", ""), focus_cho)
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
      nodes=nodes,
      edges=edges,
      focus_cho=focus_cho,
      active_meta_view=active_meta_view,
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

        import_ready = True
        detected_count = len(existing_memory_md)
        notice_level = "success"
        notice_message = "File loaded. Existing memory metadata has been prefilled."

      elif stage == "confirm":
        temp_path = request.form.get("temp_path", "").strip()
        if not temp_path or not os.path.exists(temp_path):
          return _redirect_with_notice("import_memory", "error", "Import session expired. Please upload the file again.")

        suggested_id = request.form.get("id", "").strip() or str(uuid.uuid4())[:8]
        if session.query(Memory).filter(Memory.custom_id == suggested_id).first() is not None:
          notice_level = "error"
          notice_message = f"Memory ID '{suggested_id}' already exists. Choose another ID."
          import_ready = True
          with open(temp_path, encoding="utf-8", errors="replace") as handle:
            txt = handle.read()
          existing_memory_md = _extract_memory_block_metadata(txt)
          detected_count = len(existing_memory_md)
          for field in IMPORT_FIELDS:
            form_metadata[field] = request.form.get(field, "").strip() or existing_memory_md.get(field, "")
        else:
          try:
            with open(temp_path, encoding="utf-8", errors="replace") as handle:
              txt = handle.read()

            existing_memory_md = _extract_memory_block_metadata(txt)
            metadata = dict(existing_memory_md)
            for field in IMPORT_FIELDS:
              value = request.form.get(field, "").strip()
              if value:
                metadata[field] = value

            final_text = rebuild_memory_text(txt, metadata)
            stored_path = _write_memory_text_file(suggested_id, final_text)
            memory = Memory(
              custom_id=suggested_id,
              title=metadata.get("dc:title", suggested_id),
              text=final_text,
              file_path=stored_path,
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
    )

  @app.route("/memories/<int:memory_id>/edit", methods=["POST"])
  def edit_memory(memory_id):
    memory = session.get(Memory, memory_id)
    if memory is None:
      return _redirect_with_notice("index", "error", "Memory not found.")

    focus_cho = request.form.get("focus_cho", "").strip()
    active_meta_view = _resolve_meta_view(request.form.get("meta_view", "memory"), focus_cho)
    if "title" in request.form:
      memory.title = request.form.get("title", "").strip() or (memory.title or f"Memory {memory.id}")

    posted_text = request.form.get("text")
    updated_text = posted_text if posted_text is not None else (memory.text or "")
    memory_metadata_ops = False

    deleted_memory_fields = set()
    deleted_cho_fields = set()
    metadata_map = _memory_metadata_dict(updated_text)

    for key in request.form:
      if key.startswith("delete_memory_metadata[") and key.endswith("]"):
        memory_metadata_ops = True
        field = key[len("delete_memory_metadata["):-1]
        deleted_memory_fields.add(field)
        metadata_map.pop(field, None)
        updated_text = _remove_metadata_tag(updated_text, field, MetadataType.MEMORY.value)
      elif key.startswith("delete_cho_metadata[") and "]" in key:
        remainder = key[len("delete_cho_metadata["):]
        cho_id, field = remainder.split("][")
        field = field[:-1]
        deleted_cho_fields.add((cho_id, field))
        updated_text = _remove_metadata_tag(updated_text, field, MetadataType.CHO.value, cho=cho_id)
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

    if memory_metadata_ops:
      if metadata_map:
        updated_text = rebuild_memory_text(updated_text, metadata_map)
      else:
        updated_text = _strip_memory_metadata_block(updated_text).strip()

    _persist_memory_to_disk(memory, updated_text)
    if "title" not in request.form:
      memory.title = get_memory_title(memory.text or "", memory.title or f"Memory {memory.id}")
    session.add(memory)
    session.commit()
    redirect_kwargs = {"memory_id": memory_id, "meta_view": active_meta_view}
    if focus_cho:
      redirect_kwargs["focus_cho"] = focus_cho
    return _redirect_with_notice("index", "success", "Memory metadata saved.", **redirect_kwargs)

  @app.route("/memories/<int:memory_id>/annotate", methods=["POST"])
  def annotate_memory(memory_id):
    memory = session.get(Memory, memory_id)
    if memory is None:
      return _redirect_with_notice("index", "error", "Memory not found.")

    focus_cho = request.form.get("focus_cho", "").strip()
    active_meta_view = _resolve_meta_view(request.form.get("meta_view", "memory"), focus_cho)

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
      _persist_memory_to_disk(memory)
      session.add(memory)
      session.commit()
      redirect_kwargs = {"memory_id": memory_id, "meta_view": active_meta_view}
      if focus_cho:
        redirect_kwargs["focus_cho"] = focus_cho
      return _redirect_with_notice("index", "success", "Annotation added.", **redirect_kwargs)

    redirect_kwargs = {"memory_id": memory_id, "meta_view": active_meta_view}
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
    active_meta_view = _resolve_meta_view(request.args.get("meta_view", ""), focus_cho)
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
      nodes=nodes,
      edges=edges,
      focus_cho=focus_cho,
      active_meta_view=active_meta_view,
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

    if selected_cho:
      field_memory_values = {}
      for memory in session.query(Memory).order_by(Memory.id):
        memory_label = f"{memory.custom_id or memory.id} - {memory.title or ('Memory ' + str(memory.id))}"
        memory_columns.append({"id": memory.id, "label": memory_label})
        for md in extract_metadata(memory.text or ""):
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
