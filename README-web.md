# CORDHISK Web Migration Prototype

This branch introduces a browser-based entrypoint for the existing CORDHISK application.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 web_app.py
```

Then open http://127.0.0.1:5000/.

## What is already available

- Dashboard with memory selection, metadata editing, annotation, and relationship graph.
- Memory import flow (`/memories/import`).
- Memory text search (`/search`) equivalent to desktop text search.
- CHO compare view (`/compare`) equivalent to desktop compare table.
- RDF exports as downloadable files:
	- Memory RDF: `/export/memory/<memory_id>.rdf`
	- CHO RDF: `/export/cho?cho_id=<id>&mode=single|all&memory_id=<id>`

## Notes

- The existing desktop Tkinter app remains unchanged.
- The web app reuses the current SQLite database and metadata parsing logic.
- Existing graph and metadata workflows are preserved while moving desktop features into browser routes.
