HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CORDHISK Web</title>
    <style>
      :root {
        --bg: #f2f6f8;
        --ink: #1b1f24;
        --brand: #0072b2;
        --brand-2: #009e73;
        --surface: #ffffff;
        --line: #cfd8df;
        --shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
      }
      body { font-family: "Avenir Next", "Segoe UI", sans-serif; margin: 0; background: radial-gradient(circle at 10% 10%, #f9fbfc 0%, var(--bg) 52%, #e8eef2 100%); color: var(--ink); }
      .shell { display: grid; grid-template-columns: 300px 1fr; min-height: 100vh; }
      .sidebar { background: linear-gradient(180deg, #0f3b5a 0%, #0d5660 100%); color: white; padding: 20px; display: flex; flex-direction: column; }
      .content { padding: 24px; }
      .card { background: var(--surface); border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: var(--shadow); border: 1px solid rgba(219, 228, 240, 0.7); }
      a { color: #005b8f; text-decoration: none; }
      .pill { display: inline-flex; align-items: center; margin: 3px; padding: 5px 10px; border-radius: 999px; background: #e2e8f0; font-size: 12px; border: 1px solid transparent; }
      .pill.memory { background: #d8ebf7; color: #005b8f; border-color: #9fcae2; }
      .pill.cho { background: #d8f1e6; color: #0f6f55; border-color: #9ad7c2; }
      .pill.add { background: #0072b2; color: white; border-color: #005b8f; cursor: pointer; font-weight: 700; min-width: 28px; justify-content: center; }
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
      .memory { fill: #56b4e9; }
      .cho { fill: #009e73; }
      .memory_metadata { fill: #d8ebf7; }
      .cho_metadata { fill: #d8f1e6; }
      .metadata-hidden { opacity: 0; visibility: hidden; pointer-events: none; }
      .metadata-visible { opacity: 1; visibility: visible; pointer-events: auto; }
      .metadata-collapsed { opacity: 0; visibility: hidden; pointer-events: none; }
      .edge-collapsed { opacity: 0; visibility: hidden; }
      .focused { stroke: #ef4444; stroke-width: 3; }
      .label { font-size: 12px; fill: #0f172a; pointer-events: none; }
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
      .metadata-inline-edit-actions { margin-top: 8px; }
      .annotation-inline-edit { display: none; margin-top: 10px; padding: 10px; border: 1px solid #bfdbfe; border-radius: 8px; background: #eff6ff; }
      .memory-mode-hide { display: none; }
      .sidebar-list { list-style: none; margin: 0; padding: 0; }
      .sidebar-list li { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
      .sidebar-list a { color: #0f172a; display: inline-block; max-width: 210px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .mini-delete { width: 24px; min-width: 24px; height: 24px; line-height: 24px; padding: 0; border-radius: 999px; background: #facc15; color: #1f2937; font-weight: 700; font-size: 14px; }
      .sidebar-action { margin-bottom: 12px; }
      .sidebar-action button { width: 100%; background: #0ea5e9; }
      .sidebar-pop { display: none; margin-top: 8px; padding: 10px; border-radius: 8px; background: rgba(15, 23, 42, 0.45); border: 1px solid rgba(148, 163, 184, 0.4); }
      .sidebar-pop label { font-size: 12px; color: #bfdbfe; display: block; margin-bottom: 2px; }
      .sidebar-pop input, .sidebar-pop select { margin-bottom: 8px; }
      .sidebar-card { background: #f8fbff; }
      .sidebar-card h3 { color: #0f172a; }
      .sidebar-button-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
      .side-btn, .side-btn:visited { display: inline-flex; align-items: center; justify-content: center; text-align: center; min-height: 34px; padding: 6px; border-radius: 8px; color: white; background: #0072b2; border: 0; font-size: 12px; font-weight: 600; }
      .side-btn.alt { background: #009e73; }
      .side-btn.disabled { pointer-events: none; opacity: 0.6; }
      .menu-toggle { display: block; width: 100%; margin-bottom: 10px; background: #0072b2; }
      .menu-toggle.active { background: #009e73; }
      .sidebar-menu.hidden { display: none; }
      .selection-value { font-style: italic; font-weight: 700; }
      .cho-tags-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
      .cho-tags-head h4 { margin: 0; }
      .list-selector { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px; }
      .list-selector button { background: #334155; font-size: 12px; padding: 6px 8px; }
      .list-selector button.active { background: #0072b2; }
      .list-panel.hidden { display: none; }
      .inline-annotation-row { display: grid; grid-template-columns: minmax(170px, 1fr) minmax(170px, 1fr) auto; gap: 8px; align-items: end; }
      .inline-annotation-row > div { min-width: 0; }
      .inline-annotation-row label { display: block; font-size: 12px; margin-bottom: 3px; }
      .inline-annotation-row input, .inline-annotation-row select { margin-bottom: 0; }
      .inline-annotation-row button { white-space: nowrap; }
      .status-msg { display: none; }
      .annotation-title { font-weight: 400; }
      .sidebar-footer-note {
        margin-top: auto;
        padding-top: 14px;
        font-size: 11px;
        line-height: 1.35;
        color: #d7e5ee;
        border-top: 1px solid rgba(215, 229, 238, 0.35);
      }
      @media (max-width: 980px) {
        .shell { grid-template-columns: 1fr; }
        .sidebar { border-bottom: 1px solid #334155; }
        .grid { grid-template-columns: 1fr; }
        .metadata-card { position: static; }
        .menu-toggle { display: block; }
        .sidebar-menu.hidden { display: none; }
        .sidebar-button-grid { grid-template-columns: 1fr; }
        .side-btn, .side-btn:visited, .sidebar-button-grid button { width: 100%; }
        .content { padding: 14px; }
        .card { padding: 12px; }
        .graph-card { min-height: auto; }
        svg { min-width: 680px; }
        .inline-annotation-row { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <aside class="sidebar">
        <h2>CORDHISK v2.1</h2>
        <p>Metadata workspace for memories & cultural heritage objects (CHO).</p>
        <button type="button" class="menu-toggle" id="toggle-menu">Menu</button>
        <div class="sidebar-menu hidden" id="sidebar-menu">
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
        </div>
        <div class="list-selector">
          <button type="button" id="show-memories-btn" class="active">Memories</button>
          <button type="button" id="show-chos-btn">CHO records</button>
        </div>
        <div class="card sidebar-card list-panel" id="memories-panel">
          <ul class="sidebar-list">
            {% for memory in memories %}
            <li>
              <a href="/?memory_id={{ memory.id }}">{{ memory.custom_id or memory.id }} — {{ memory.title or ('Memory ' ~ memory.id) }}</a>
              <form action="/memories/{{ memory.id }}/delete" method="post" onsubmit="return confirm('Delete this memory permanently?');">
                <button type="submit" class="mini-delete" title="Delete memory">-</button>
              </form>
            </li>
            {% endfor %}
          </ul>
        </div>
        <div class="card sidebar-card list-panel hidden" id="chos-panel">
          <ul class="sidebar-list">
            {% for cho in chos %}
            <li>
              <a href="/?memory_id={{ selected_memory.id if selected_memory else '' }}&focus_cho={{ cho.custom_id or cho.id }}">{{ cho.custom_id or cho.id }} — {{ cho.title or cho.custom_id or cho.id }}</a>
              <form action="/chos/{{ cho.id }}/delete{% if selected_memory %}?memory_id={{ selected_memory.id }}{% endif %}" method="post" onsubmit="return confirm('Delete this CHO and remove its tags from all memories?');">
                <button type="submit" class="mini-delete" title="Delete CHO">-</button>
              </form>
            </li>
            {% endfor %}
          </ul>
        </div>
        <p class="sidebar-footer-note">
          Developped by Rafael Ramirez Eudave at the Delft University of Technology (2026).<br>
          This project has received funding from the European Union's Horizon Europe 2023 research and innovation programme under the Marie Sklodowska Curie grant agreement No 101149833 for the project "Community-driven Digitisation for Heritage at Risk" (CORDHISK).
        </p>
      </aside>
      <main class="content">
        {% if notice_message %}
        <div class="status-msg" aria-hidden="true">{{ notice_message }}</div>
        {% endif %}
        {% if selected_memory %}
        <div class="grid">
          <div class="card graph-card">
            <h3>Memory relationship graph</h3>
            <div class="graph-toolbar">
              <button type="button" id="zoom-in" aria-label="Zoom in">+</button>
              <button type="button" id="zoom-out" aria-label="Zoom out">-</button>
              <button type="button" id="reset-view">Reset</button>
              <div id="graph-hover-value" class="graph-hover-value">Hover CHO or metadata nodes to inspect values.</div>
            </div>
            <div class="graph-shell">
              <svg id="graph-svg" viewBox="0 0 1000 700" role="img" aria-label="Memory and CHO graph">
                <g id="graph-content">
                  {% for edge in edges %}
                  <line x1="{{ edge[0].x }}" y1="{{ edge[0].y }}" x2="{{ edge[1].x }}" y2="{{ edge[1].y }}" data-from-id="{{ edge[0].id }}" data-to-id="{{ edge[1].id }}" stroke="#94a3b8" stroke-width="2"></line>
                  {% endfor %}
                  {% for node in nodes %}
                  <a href="{{ node.link }}">
                    <circle class="graph-node node {{ node.group }} {% if node.id == ('cho:' ~ focus_cho) or node.id == focus_memory %}focused{% endif %} {% if node.group in ['memory_metadata','cho_metadata'] %}metadata-visible{% endif %}" data-node-id="{{ node.id }}" data-node-type="{{ node.group }}" data-parent-id="{{ node.parent_id or '' }}" data-memory-owner-id="{{ node.memory_owner_id or '' }}" data-details="{{ node.details or '' }}" title="{{ node.details or '' }}" cx="{{ node.x }}" cy="{{ node.y }}" r="{{ node.radius or 32 }}"></circle>
                    <text class="label {% if node.group in ['memory_metadata','cho_metadata'] %}graph-metadata-label metadata-visible{% endif %}" data-node-id="{{ node.id }}" data-node-type="{{ node.group }}" data-parent-id="{{ node.parent_id or '' }}" data-memory-owner-id="{{ node.memory_owner_id or '' }}" x="{{ node.x }}" y="{{ node.y + 6 }}" text-anchor="middle">{{ node.label }}</text>
                  </a>
                  {% endfor %}
                </g>
              </svg>
            </div>
          </div>
          <div>
            {% if not focus_cho %}
            <div class="card">
              <h2>{{ selected_memory.custom_id or selected_memory.id }} — {{ selected_memory.title or ('Memory ' ~ selected_memory.id) }}</h2>
              <form action="/memories/{{ selected_memory.id }}/annotate" method="post">
                <h3 class="annotation-title">Annotate highlighted memory text</h3>
                <div class="annotation-toolbar">
                  <button type="button" class="pill add" id="open-add-cho-tag" title="Add CHO tag">+</button>
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
                <input id="selected-annotation-text" name="selected_annotation_text" type="hidden">
                <div id="add-cho-tag-box" class="annotation-inline-edit">
                <div class="inline-annotation-row">
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
                </div>
                <input type="hidden" name="focus_cho" value="{{ focus_cho or '' }}">
              </form>
            </div>
            {% endif %}
            <div class="card metadata-card">
              {% if focus_cho and selected_cho_details %}
                <h4>CHO {{ selected_cho_details.label }} — {{ selected_cho_details.title }}</h4>
                <p>Metadata grouped by memory for the selected CHO.</p>
                {% for group in selected_cho_details.memories %}
                <div class="cho-memory-group">
                  <p><strong><a href="/?memory_id={{ group.memory_id }}&focus_cho={{ selected_cho_details.label }}">{{ group.memory_label }}</a></strong></p>
                  <div class="tag-list">
                    {% for tag in group.tags %}
                    <span class="pill cho">{{ tag.field }}: {{ tag.value }}</span>
                    {% endfor %}
                  </div>
                </div>
                {% else %}
                <p>No metadata found for this CHO in the current memories.</p>
                {% endfor %}
              {% elif focus_cho %}
                <p>Select a CHO from the sidebar or graph to view CHO metadata grouped by memory.</p>
              {% else %}
                <form action="/memories/{{ selected_memory.id }}/edit" method="post" id="memory-metadata-form">
                  <input type="hidden" name="focus_cho" value="{{ focus_cho or '' }}">
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
                      <div class="metadata-inline-edit-actions">
                        <button type="submit">Save metadata changes</button>
                      </div>
                  </div>

                  <div class="tag-section">
                      <div class="cho-tags-head">
                        <button type="submit" name="remove_selected" value="1" onclick="return confirm('Remove selected metadata tags?');">Remove selected tags</button>
                        <h4>CHO tags in this memory</h4>
                      </div>
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
        const isChoView = {{ 'true' if focus_cho else 'false' }};
        const source = document.getElementById('annotation-source');
        const target = document.getElementById('selected-annotation-text');
        const preview = document.getElementById('selection-preview');
        const addChoTagButton = document.getElementById('open-add-cho-tag');
        const addChoTagBox = document.getElementById('add-cho-tag-box');
        const menuToggleButton = document.getElementById('toggle-menu');
        const sidebarMenu = document.getElementById('sidebar-menu');
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
        const showMemoriesBtn = document.getElementById('show-memories-btn');
        const showChosBtn = document.getElementById('show-chos-btn');
        const memoriesPanel = document.getElementById('memories-panel');
        const chosPanel = document.getElementById('chos-panel');
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
            if (target) {
              target.value = '';
            }
            return;
          }
          if (target) {
            target.value = selection;
          }
          preview.innerHTML = 'Selection: <span class="selection-value"></span>';
          const valueSpan = preview.querySelector('.selection-value');
          if (valueSpan) {
            valueSpan.textContent = selection;
          }
        }

        if (source && target && preview) {
          source.addEventListener('mouseup', function () { setTimeout(captureSelection, 0); });
        }

        if (addChoTagButton && addChoTagBox) {
          addChoTagButton.addEventListener('click', function () {
            captureSelection();
            const isVisible = addChoTagBox.style.display === 'block';
            addChoTagBox.style.display = isVisible ? 'none' : 'block';
          });
        }

        if (menuToggleButton && sidebarMenu) {
          const syncMenu = function () {
            if (!menuToggleButton.classList.contains('active')) {
              sidebarMenu.classList.add('hidden');
            }
          };
          menuToggleButton.addEventListener('click', function () {
            const open = menuToggleButton.classList.toggle('active');
            sidebarMenu.classList.toggle('hidden', !open);
          });
          window.addEventListener('resize', syncMenu);
          syncMenu();
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

        if (showMemoriesBtn && showChosBtn && memoriesPanel && chosPanel) {
          const selectList = function (target) {
            const showMemories = target === 'memories';
            memoriesPanel.classList.toggle('hidden', !showMemories);
            chosPanel.classList.toggle('hidden', showMemories);
            showMemoriesBtn.classList.toggle('active', showMemories);
            showChosBtn.classList.toggle('active', !showMemories);
          };
          showMemoriesBtn.addEventListener('click', function () { selectList('memories'); });
          showChosBtn.addEventListener('click', function () { selectList('chos'); });
          {% if focus_cho %}
          selectList('chos');
          {% else %}
          selectList('memories');
          {% endif %}
        }

        if (memoryMetadataForm) {
          memoryMetadataForm.addEventListener('submit', function (event) {
            const deleteInputs = Array.from(memoryMetadataForm.querySelectorAll('input[type="checkbox"][name^="delete_"]'));
            const hasDeletion = deleteInputs.some((input) => input.checked);
            const submitter = event.submitter;
            const explicitRemove = submitter && submitter.name === 'remove_selected';
            if ((hasDeletion || explicitRemove) && !window.confirm('Confirm removal of selected metadata tags?')) {
              event.preventDefault();
            }
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
              setHoverValue('Hover CHO or metadata nodes to inspect values.');
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
          const metadataLabels = Array.from(document.querySelectorAll('.graph-metadata-label[data-node-type="memory_metadata"], .graph-metadata-label[data-node-type="cho_metadata"]'));
          const allNodeCircles = Array.from(document.querySelectorAll('.graph-node[data-node-id]'));
          const allNodeLabels = Array.from(document.querySelectorAll('.label[data-node-id]'));
          const edgeLines = Array.from(document.querySelectorAll('line[data-from-id][data-to-id]'));
          const nodeCircleById = new Map(allNodeCircles.map((node) => [node.getAttribute('data-node-id') || '', node]));
          const nodeLabelById = new Map(allNodeLabels.map((node) => [node.getAttribute('data-node-id') || '', node]));
          const originalYById = new Map(allNodeCircles.map((node) => [node.getAttribute('data-node-id') || '', parseFloat(node.getAttribute('cy') || '0')]));
          const collapsedByMemory = new Set();
          const collapsedByCho = new Set();
          const setHoverValue = (text) => {
            if (hoverValueBox) {
              hoverValueBox.textContent = text || 'No metadata details available.';
            }
          };
          const setNodeY = (nodeId, y) => {
            const circle = nodeCircleById.get(nodeId);
            if (circle) {
              circle.setAttribute('cy', String(y));
            }
            const label = nodeLabelById.get(nodeId);
            if (label) {
              label.setAttribute('y', String(y + 6));
            }
          };
          const updateEdges = () => {
            edgeLines.forEach((line) => {
              const fromId = line.getAttribute('data-from-id') || '';
              const toId = line.getAttribute('data-to-id') || '';
              const fromNode = nodeCircleById.get(fromId);
              const toNode = nodeCircleById.get(toId);
              if (!fromNode || !toNode) {
                return;
              }
              line.setAttribute('x1', fromNode.getAttribute('cx') || '0');
              line.setAttribute('y1', fromNode.getAttribute('cy') || '0');
              line.setAttribute('x2', toNode.getAttribute('cx') || '0');
              line.setAttribute('y2', toNode.getAttribute('cy') || '0');
              const collapsed = fromNode.classList.contains('metadata-collapsed') || toNode.classList.contains('metadata-collapsed');
              line.classList.toggle('edge-collapsed', collapsed);
            });
          };
          const compactLayout = () => {
            const choNodes = allNodeCircles
              .filter((node) => node.getAttribute('data-node-type') === 'cho')
              .sort((a, b) => (originalYById.get(a.getAttribute('data-node-id') || '') || 0) - (originalYById.get(b.getAttribute('data-node-id') || '') || 0));
            let cursorY = 140;
            const rowGap = 64;
            choNodes.forEach((choNode) => {
              const choId = choNode.getAttribute('data-node-id') || '';
              const choMetadata = metadataNodes
                .filter((node) => (node.getAttribute('data-parent-id') || '') === choId)
                .sort((a, b) => (originalYById.get(a.getAttribute('data-node-id') || '') || 0) - (originalYById.get(b.getAttribute('data-node-id') || '') || 0));
              const visibleMetadata = choMetadata.filter((node) => !node.classList.contains('metadata-collapsed'));
              const visibleCount = visibleMetadata.length;
              const choY = visibleCount > 0 ? cursorY + ((visibleCount - 1) * rowGap) / 2 : cursorY + 35;
              setNodeY(choId, choY);
              visibleMetadata.forEach((node, index) => {
                const nodeId = node.getAttribute('data-node-id') || '';
                setNodeY(nodeId, cursorY + index * rowGap);
              });
              const bandHeight = visibleCount > 0 ? Math.max(170, visibleCount * rowGap + 55) : 110;
              cursorY += bandHeight;
            });
            updateEdges();
          };
          const applyCollapsedState = () => {
            const allMetadata = metadataNodes.concat(metadataLabels);
            allMetadata.forEach((item) => {
              const ownerMemoryId = item.getAttribute('data-memory-owner-id') || '';
              const ownerChoId = item.getAttribute('data-parent-id') || '';
              const collapsed = isChoView ? collapsedByMemory.has(ownerMemoryId) : collapsedByCho.has(ownerChoId);
              item.classList.toggle('metadata-collapsed', collapsed);
            });
            compactLayout();
          };

          const initiallyVisibleMetadataNode = metadataNodes.find((node) => node.classList.contains('metadata-visible'));
          if (initiallyVisibleMetadataNode) {
            setHoverValue(initiallyVisibleMetadataNode.getAttribute('data-details'));
          }

          const nodeElements = Array.from(document.querySelectorAll('.graph-node'));
          nodeElements.forEach((node) => {
            node.addEventListener('mouseenter', function () {
              setHoverValue(node.getAttribute('data-details'));
            });
            node.addEventListener('click', function (event) {
              const nodeType = node.getAttribute('data-node-type');
              const nodeId = node.getAttribute('data-node-id') || '';
              if (isChoView && nodeType === 'memory') {
                event.preventDefault();
                if (collapsedByMemory.has(nodeId)) {
                  collapsedByMemory.delete(nodeId);
                } else {
                  collapsedByMemory.add(nodeId);
                }
                applyCollapsedState();
                setHoverValue(node.getAttribute('data-details'));
                return;
              }
              if (!isChoView && nodeType === 'cho') {
                event.preventDefault();
                if (collapsedByCho.has(nodeId)) {
                  collapsedByCho.delete(nodeId);
                } else {
                  collapsedByCho.add(nodeId);
                }
                applyCollapsedState();
                setHoverValue(node.getAttribute('data-details'));
                return;
              }
              if (nodeType === 'cho' || nodeType === 'memory') {
                setHoverValue(node.getAttribute('data-details'));
              }
            });
          });

          metadataNodes.forEach((node) => {
            node.addEventListener('mouseenter', function () {
              setHoverValue(node.getAttribute('data-details'));
            });
            node.addEventListener('click', function (event) {
              event.preventDefault();
              setHoverValue(node.getAttribute('data-details'));
            });
          });

          applyCollapsedState();
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
                <th><a href="/?memory_id={{ memory.id }}&focus_cho={{ selected_cho }}">{{ memory.label }}</a></th>
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
      .status-msg { display: none; }
    </style>
  </head>
  <body>
    <div class="wrap">
      {% if notice_message %}
      <div class="status-msg" aria-hidden="true">{{ notice_message }}</div>
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
