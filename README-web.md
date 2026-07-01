# CORDHISK Web Migration Prototype

This branch introduces a browser-based entrypoint for the existing CORDHISK application.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 web_app.py
```

Then open http://127.0.0.1:5000/.

## Notes

- The existing desktop Tkinter app remains unchanged.
- The web prototype reuses the current SQLite database and metadata parsing logic.
- The next step is to expand this into a full multi-page experience with editing, search, and export tools.
