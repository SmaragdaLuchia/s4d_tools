# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A tool for parsing and visualizing **StanForD** forest-harvester data files. It supports two format families:

- **StanForD Classic** — tilde-separated text files: `.prd` (production), `.pri` (production-individual), `.apt` (bucking/price instructions), `.stm` (stems).
- **StanForD 2010** — XML files: `.hpr` (harvested production), `.pin` (product instructions).

The primary interface is a Streamlit web app; `s4d_tools` is the reusable Python library underneath it.

## Commands

```bash
# Install (Python 3.11+)
pip install -e .                         # development install from repo
pip install -e ".[dev]"                  # with test dependencies
pip install streamlit                    # Streamlit UI dependencies (no extra defined for these)
pip install s4d-tools                    # from PyPI (when published)

# Run the app (requires Streamlit installation)
python -m streamlit run streamlit/app.py

# Tests
pytest tests/ -v                         # full suite
pytest tests/test_hpr_parser.py -v       # one file
pytest tests/test_prd_parser.py::TestPRDParser::test_parse_objects   # one test
```

The package is configured for PyPI distribution via `pyproject.toml`. Run everything from the repo root.

## Architecture

Data flows through a strict one-directional pipeline. Understanding the **standardized report** is the key to the whole codebase:

```
parsers/  ──►  transformers/ (standardized report)  ──►  aggregators/  ──►  streamlit/ (UI)
```

### 1. Parsers (`s4d_tools/parsers/`)
Each parser reads one file format and returns a `dict[str, pd.DataFrame]` keyed by section (`header`, `machine`, `objects`, `stems`, `logs`, ...). Public classes are re-exported from `s4d_tools/__init__.py`: `APTParser`, `PRDParser`, `PRIParser`, `HPRParser`, `PINParser`.

- **`stanford_classic/`** — parsers call `utils/helpers.load_raw_data()`, which splits the file on `~` (`BLOCK_SEPARATOR`) and builds a `{(group_id, variable_id): value}` map. Repeated keys merge into lists (`merge_duplicate_keys=True`). Parsers then pull known `(group, variable)` pairs via `_get_value()` and shape them into DataFrames. Default encoding is `iso-8859-15` (`constants.DEFAULT_ENCODING`). `PRI_LOG_CODES` in `constants.py` maps numeric log codes to column names for the dynamic PRI `logs` table.
- **`stanford_2010/`** — parsers use `xml.etree.ElementTree` with the namespace map `STANFORD_2010_NS` (`{"s": "urn:skogforsk:stanford2010"}`). `utils/helpers.get_text()` is the null-safe element-text accessor used throughout.

### 2. Transformers (`s4d_tools/transformers/`) — the central abstraction
`standardized_schema.py` defines the **standardized report**: a `dict` of DataFrames with fixed column sets (`STANDARDIZED_*_COLUMNS`) plus two metadata keys, `META_SOURCE_TYPE` and `META_HAS_PRI`. This is the *only* shape the UI consumes — every source format is normalized into it.

`to_standardized.py` has two kinds of functions:
- `transform_<fmt>_to_standardized(...)` — build a base report from one primary source (PRD or HPR).
- `merge_<fmt>_into_standardized(base, ...)` — layer optional secondary sources (PRI, PIN, APT) onto an existing report. PRI merging fills missing header/machine/object fields and adds log-level and species×product volume tables; PIN/APT supply the pricing matrix.

`apt_pricematrix_normalization.py` converts the various APT price-matrix shapes into the standardized long-form `price_matrix` table.

When adding a new field to the UI, it must be threaded through the standardized schema columns here — parsers producing a column that isn't in `STANDARDIZED_*_COLUMNS` will be dropped by `_ensure_columns`/`_format_table` (except `stems`, which explicitly preserves extra columns).

### 3. Aggregators (`s4d_tools/aggregators/`)
Pure functions over standardized DataFrames → chart-ready frames (stems by species, volume by species×product, price-matrix heatmaps). No parsing or I/O.

### 4. Streamlit apps (`streamlit/`)
`app.py` and `app_et.py` are the two entry points. They: accept uploads, save them to temp files, call the appropriate parser, run the matching `transform_*` / `merge_*` functions, and render the standardized report via `visualize_data()`. `chart_utils.py` holds Altair chart builders and productivity-rate calculations. A second tab uses `utils/sanitize_stanford_2010.py` for GDPR redaction of StanForD 2010 XML (operates directly on the XML tree, independent of the parser pipeline).

**Note:** `app_et.py` is largely a duplicate of `app.py` (Estonian labels, minus some features). Changes to shared UI logic must currently be made in both files.

## Conventions

- Parsers return DataFrames, never raw dicts — sections that don't exist return an *empty* DataFrame, not `None`. Downstream code guards with `.empty` checks rather than `None` checks.
- Classic-format `(group_id, variable_id)` numbers are the canonical field identity. API documentation is available at https://s4d-tools.pages.dev.
- Test fixtures (`tests/fixtures/toy_test.{hpr,prd,pri}`) are hand-crafted minimal files; parser tests assert exact expected values against them, so fixture edits require matching test updates.
