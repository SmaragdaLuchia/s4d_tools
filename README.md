# s4d_tools — StanForD Parser

A Python library and web-based visualization tool for analyzing StanForD (Standard for Forest Data) harvester files. `s4d_tools` parses production data from forest harvesters, normalizes every supported format into one standardized report shape, and provides aggregations for analysis — with an optional Streamlit app on top.

**Documentation:** <https://smaragdaluchia.github.io/s4d_tools/#/>

## Features

- **File parsing** for both StanForD format families:
  - `.prd` — production summary (Classic)
  - `.pri` — production-individual, log-level detail (Classic, combine with PRD)
  - `.apt` — bucking / price instructions (Classic, adds the relative price matrix)
  - `.hpr` — harvested production (StanForD 2010 XML)
  - `.pin` — product instructions (StanForD 2010 XML, adds the price matrix for HPR)
- **Standardized report**: every format is transformed into the same dict-of-DataFrames schema, so downstream code never cares which file type the data came from
- **Aggregations**: stems by species, volume by species × product, price-matrix heatmaps, productivity rates

## Quickstart (run the web app)

The fastest way to explore your harvester files — no coding required.

```bash
git clone https://github.com/SmaragdaLuchia/s4d_tools.git
cd s4d_tools
pip install -e . streamlit
python -m streamlit run streamlit/app.py
```

Requires Python 3.11+. No harvester files at hand? Grab the **[sample files (.zip)](https://smaragdaluchia.github.io/s4d_tools/samples/s4d-tools-samples.zip)** — one per supported format, all describing the same small harvest.

### Using the application

1. Upload a `.prd` or `.hpr` file (try the sample files above)
2. Optionally add a `.pri` file (with PRD) and/or `.apt` / `.pin` files for price matrices
3. Explore the parsed data through the interactive tabs:
   - **Overview** — summary statistics and key metrics
   - **Basic Info** — file header and object information
   - **Species** — species groups and distribution
   - **Products** — product information
   - **Statistics** — production statistics and assortment breakdown
   - **Price matrix** — per-assortment diameter × length matrices (when APT/PIN uploaded)
   - **Machine / Stems / Logs** — machine specs and row-level data
4. The **Data redaction (GDPR)** tab produces a copy of a StanForD 2010 XML file with sensitive fields replaced by a placeholder

## Quickstart (use the library)

Full walkthrough with explanations: **<https://smaragdaluchia.github.io/s4d_tools/#/quickstart>**

### 1. Install

Requires Python 3.11+.

```bash
pip install s4d-tools
```

### 2. Get files to test with

No harvester files at hand? Download the sample files — one per supported format, all describing the same small harvest:

**[Download sample files (.zip)](https://smaragdaluchia.github.io/s4d_tools/samples/s4d-tools-samples.zip)**

Extract the archive so the `s4d-tools-samples/` folder sits next to your script.

### 3. Parse, standardize, aggregate

```python
from s4d_tools import (
    HPRParser,
    transform_hpr_to_standardized,
    aggregate_stems_by_species,
)

raw = HPRParser("s4d-tools-samples/sample.hpr").parse()
report = transform_hpr_to_standardized(raw)

print(report["species_table"])
#   species_name  stems  volume_m3
# 0         Pine      3      1.870
# 1       Spruce      2      1.105

print(aggregate_stems_by_species(report["stems"], report["species_groups"]))
#   species_name  stem_count
# 0         Pine           3
# 1       Spruce           2
```

More recipes — combining PRD + PRI, adding price matrices from APT, exporting to CSV/Excel — are in [EXAMPLE_USAGE.md](EXAMPLE_USAGE.md).

## Development setup (work on the code)

### 1. Clone the repository

```bash
git clone https://github.com/SmaragdaLuchia/s4d_tools.git
cd s4d_tools
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv

# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

### 3. Install in editable mode

```bash
pip install --upgrade pip
pip install -e ".[dev]"      # library + test dependencies
pip install streamlit        # add the Streamlit UI (optional)
```

### 4. Run the tests

```bash
pytest tests/ -v
```

Test fixtures live in `tests/fixtures/` — they are hand-crafted minimal files, and the parser tests assert exact values against them. The downloadable sample files (`docs-site/public/samples/`) are richer variants meant for trying the library out.

To run the Streamlit app from your development install, see the [web app Quickstart](#quickstart-run-the-web-app) above.
