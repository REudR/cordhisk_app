# Cordhisk App

A desktop application for annotating textual memories and linking them to Cultural Heritage Objects (CHOs) through structured metadata.

Features

- Annotate text with semantic metadata (Dublin Core)
- Link annotations to CHOs
- Graph visualization of relationships
- Explore metadata by Memory or CHO
- Multi-language annotation support

## Installation

1. Clone the repository:

```bash
git clone https://github.com/REudR/cordhisk_app.git
cd cordhisk_app

![App Screenshot](screenshot.png)

2. Install dependencies

pip install -r requirements.txt

3. Run the app

python main.py
```
## Usage

Select a memory → see annotations
Click CHO → explore all related metadata
Use graph view to navigate relationships

## Project structure

ui/ → interface components
features/ → graph, search, export
services/ → parsing, metadata logic
state.py → shared app state

## About

Copyright (c) 2026 Rafael Ramírez Eudave. See LICENSE file.
This code has been produced at the Delft University of Technology with the support of Microsoft Copilot.

This code and the data herein contained represents a development based on the following research: Ramírez Eudave, R., Ferreira, T.M. & Giardina, G. Communities co-creating metadata: a new paradigm towards FAIR everyday heritage. npj Herit. Sci. (2026). https://doi.org/10.1038/s40494-026-02706-1
This project has received funding from the European Union’s Horizon Europe 2023 research and innovation programme under the Marie Skłodowska Curie grant agreement No 101149833 for the project «Community-driven Digitisation for Heritage at Risk» (CORDHISK).
