# CORDHISK

CORDHISK is a browser-based application for annotating textual memories and connecting their passages to Cultural Heritage Objects (CHOs) through structured metadata.

For a complete functional and technical description suitable for project documentation or a thesis appendix, see [Design, Operation, and Capabilities](ARCHITECTURE.md).

## Run locally

Requires Python 3.10 or later.

```bash
git clone https://github.com/r-eudave/cordhisk_app.git
cd cordhisk_app
python3 -m pip install -r requirements.txt
python3 cordhisk.py
```

Open http://127.0.0.1:5000/ in a browser. The application runs with Flask's development server.

## Capabilities

- Create, edit, delete, and browse memories and CHOs.
- Import `.txt` memories while preserving or completing embedded memory metadata.
- Annotate selected memory text with CHO metadata from Dublin Core, DCTERMS, OAF, and RDA vocabularies.
- Edit memory metadata, including identifiers and usage licenses, and manage individual CHO tags.
- Navigate relationships in interactive Memory and CHO views, including a relationship graph.
- Filter the CHO tags displayed for a selected memory.
- Search memory text with paginated results.
- Compare one CHO across its related memories in a field-by-memory matrix.
- Generate a CHO report grouped by metadata field and instance frequency, with links to related memories and CSV download.
- Export Memory and CHO metadata as downloadable RDF/XML.

## Data storage

CORDHISK stores its SQLite database and memory text files in `memory_files/`. Back up this directory to preserve application data.

## Development

Run the automated web application tests with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Project structure

- `cordhisk.py`: Flask application and HTTP routes.
- `services/`: metadata parsing, schema definitions, data types, memory rebuilding, and HTML templates.
- `memory_files/`: application-managed memory text files and SQLite database.
- `tests/`: automated Flask application tests.

## About

Copyright (c) 2026 Rafael Ramírez Eudave. See [LICENSE](LICENSE).

This code was produced at Delft University of Technology with support from Microsoft Copilot. It builds on: Ramírez Eudave, R., Ferreira, T.M. & Giardina, G. Communities co-creating metadata: a new paradigm towards FAIR everyday heritage. *npj Heritage Science* (2026). https://doi.org/10.1038/s40494-026-02706-1

This project received funding from the European Union's Horizon Europe 2023 research and innovation programme under Marie Sklodowska-Curie grant agreement No. 101149833 for the project Community-driven Digitisation for Heritage at Risk (CORDHISK).
