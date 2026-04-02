# MatSci Explorer

An interactive Streamlit dashboard for exploring crystal structures, electronic, mechanical, and optical properties of materials sourced from the [Materials Project](https://materialsproject.org) database — with local SQLite caching, 3D visualization, XRD simulation, percentile ranking, and Ashby material-selection charts.

---

## Purpose & Goal

MatSci Explorer makes computational materials science accessible and visual. It lets you:

- Browse 24 hand-curated compounds across 6 categories (magnets, perovskites, semiconductors, space elevator candidates, ultra-high temperature ceramics, superconductors)
- Fetch and cache thousands more compounds from the Materials Project API
- Compare any compound's properties against the full database with percentile rank bars and a position scatter chart
- Explore structure–property relationships through Ashby charts and an interactive 3D crystal viewer
- Understand *why* each material works via plain-English explanations in `compounds.py`

---

## Installation

**Prerequisites:** Python 3.10+, a free [Materials Project API key](https://materialsproject.org/api)

```bash
# 1. Clone / download the project folder
cd kmatsci040226

# 2. Install dependencies
pip install streamlit mp-api pymatgen plotly python-dotenv requests

# 3. Create a .env file with your API key
echo MP_API_KEY=your_key_here > .env

# 4. Populate the local database (one-time, ~10–30 min depending on fetch size)
python fetch.py

# 5. Launch the dashboard
streamlit run app.py
```

The app runs entirely from `matsci.db` after the first fetch — no live API calls are needed to browse cached compounds.

---

## Project Structure

```
kmatsci040226/
├── app.py          # Streamlit dashboard (UI, charts, layout)
├── fetch.py        # One-time data fetcher from Materials Project API
├── db.py           # SQLite database layer (schema, queries, migrations)
├── compounds.py    # Curated compound catalog with explanations
├── pubchem.py      # PubChem cross-reference for experimental properties
├── matsci.db       # Local SQLite database (auto-created by fetch.py)
├── cache/          # JSON structure cache (fallback if DB structure missing)
└── .env            # API key (MP_API_KEY=...)
```

---

## File Reference

### `app.py` — Dashboard UI

The main Streamlit application. Renders a zero-scroll single-viewport layout with a sidebar compound list and a main panel grid.

**Constants & configuration**

| Name | Description |
|------|-------------|
| `HELP` | Dict of 22 property names → plain-English tooltip strings shown on `?` labels. |
| `COL_BOUNDS` | Dict of DB column names → SQL WHERE clauses used to filter outliers before building percentile rank distributions. |
| `POS_PROPS` | Dict mapping human-readable axis labels to DB column names for the position/comparison scatter chart. |
| `POS_KEYS` | Ordered list of axis label strings used to populate X/Y selectboxes. |

**Cached data functions**

| Function | Description |
|----------|-------------|
| `col_stats(col)` | Returns a dict with a sorted list of all non-null values for a DB column and the total compound count; cached at startup for instant percentile lookups. |
| `load_structure(mp_id, api_key)` | Loads a pymatgen `Structure` from the local DB, then the file cache, then the live API as a last resort, storing results locally on first fetch. |
| `get_xrd(structure_json)` | Runs a CuKα XRD simulation on a serialized structure and returns peak positions, intensities, and (hkl) labels; cached to avoid recomputing on every render. |
| `get_pubchem(formula, name)` | Fetches experimental properties from PubChem for a given formula/name; cached per session. |
| `_pos_data(x_col, y_col, fm, cs, tag)` | Cached wrapper around `db.get_position_data` for the comparison scatter chart. |
| `_ashby(x, y, c, lim)` | Cached wrapper around `db.get_ashby_data` for the Ashby chart view. |

**Helper functions**

| Function | Description |
|----------|-------------|
| `pct_rank(raw_val, col)` | Returns "top X%" as a float (0–100) using binary search on cached sorted values; inverts rank for lower-is-better columns (formation energy, hull energy). |
| `_rank_color(top_pct)` | Returns a hex color (green/yellow/red) based on how good the percentile rank is. |
| `_default()` | Returns the mp_id, name, and data dict for the first compound in the first category, used to initialize session state. |
| `_auto_axes(tags)` | Suggests sensible default X/Y axes for the comparison chart based on the compound's category tags. |
| `_f(v, fmt)` | Formats a numeric value to a string with a given format spec, returning `"—"` for None. |
| `badge(text, style)` | Returns an HTML `<span>` badge with optional color style (green/orange/red/blue). |
| `sc(label, value, note, col, raw, tip)` | Returns an HTML stat-card `<div>` with optional percentile rank bar and hover tooltip. |
| `sh(text)` | Returns an HTML section-header `<div>`. |
| `na(msg)` | Returns an HTML not-available italic message `<div>`. |
| `kpi(label, value, unit)` | Returns an HTML KPI tile `<div>` for the top summary strip. |
| `panel(html, height)` | Wraps an HTML string in a fixed-height scrollable `<div>` container. |
| `render_crystal(structure, accent, w, h)` | Generates a self-contained HTML page with a 3Dmol.js 3D crystal viewer (spinning, ball-and-stick, unit cell outline). |

**Panel HTML builders**

| Function | Description |
|----------|-------------|
| `build_electronic(row)` | Builds the HTML string for the Electronic & Magnetic property panel from a DB row dict. |
| `build_mechanical(row)` | Builds the HTML string for the Elastic Moduli & Thermal property panel from a DB row dict. |
| `build_dielectric(row)` | Builds the HTML string for the Dielectric & Optical property panel from a DB row dict. |
| `build_stability(row, pc_data)` | Builds the HTML string for the Thermodynamic Stability & Physical panel, including PubChem data if available. |
| `render_position_chart(db_row, accent, chart_h)` | Renders the "Where does this compound sit?" scatter chart inline with X/Y selectboxes and a filter radio button. |

---

### `db.py` — Database Layer

SQLite schema, migrations, and all query functions. The database lives at `matsci.db` next to the project files.

| Function | Description |
|----------|-------------|
| `get_conn()` | Opens and returns a connection to `matsci.db`. |
| `init_db()` | Creates the `materials` table if it doesn't exist, then runs `migrate_db()`. |
| `migrate_db()` | Adds new columns to an existing database without losing data; safe to call on any schema version. |
| `upsert(...)` | Inserts or replaces a full material record including all core and extended fields. |
| `has_material(mp_id)` | Returns True if the given mp_id already exists in the database. |
| `get_structure(mp_id)` | Loads and returns a pymatgen `Structure` object from the serialized JSON in the database. |
| `get_material_row(mp_id)` | Returns all database fields for one compound as a plain Python dict. |
| `save_pubchem(mp_id, data)` | Stores a PubChem property dict as JSON in the database for a given compound. |
| `save_elasticity(mp_id, ...)` | Stores mechanical/thermal properties (bulk modulus, shear modulus, Young's modulus, Poisson ratio, anisotropy, thermal conductivity, Debye temperature) and marks the compound as fetched. |
| `save_dielectric(mp_id, ...)` | Stores dielectric/optical properties (total ε, ionic ε, electronic ε, refractive index) and marks the compound as fetched. |
| `search(...)` | Queries the database by crystal system, bandgap range, magnetization, or tag with a configurable result limit. |
| `get_ashby_data(x_col, y_col, color_col, limit)` | Returns compounds with non-null values for both axis columns, used to populate Ashby material selection charts. |
| `get_position_data(x_col, y_col, filter_mode, ...)` | Returns compounds for the position/comparison scatter chart, with optional filtering by crystal system or category tag. |
| `stats()` | Returns a summary dict with total compound count and counts for those with bandgap, structure, elasticity, and dielectric data. |

**Database schema** (`materials` table, key columns):

| Column | Type | Description |
|--------|------|-------------|
| `mp_id` | TEXT PK | Materials Project ID (e.g. `mp-149`) |
| `formula` | TEXT | Chemical formula (e.g. `Si`) |
| `crystal_system` | TEXT | Cubic, Hexagonal, Tetragonal, etc. |
| `space_group` | TEXT | Hermann-Mauguin symbol (e.g. `Fd-3m`) |
| `bandgap` | REAL | DFT band gap in eV |
| `is_direct_gap` | INTEGER | 1=direct, 0=indirect, NULL=unknown |
| `total_magnetization` | REAL | Net magnetic moment in μB/f.u. |
| `formation_energy_per_atom` | REAL | eV/atom (negative = stable vs elements) |
| `energy_above_hull` | REAL | eV/atom above convex hull (0 = ground state) |
| `structure_json` | TEXT | Full pymatgen Structure serialized as JSON |
| `k_voigt` | REAL | Voigt bulk modulus in GPa |
| `g_voigt` | REAL | Voigt shear modulus in GPa |
| `young_modulus` | REAL | Young's modulus in GPa |
| `e_total` | REAL | Static dielectric constant |
| `refractive_index` | REAL | Optical refractive index n = √ε∞ |
| `thermal_conductivity` | REAL | W/m·K (Clarke/Cahill average estimate) |
| `debye_temperature` | REAL | Debye temperature in K |
| `elastic_fetched` | INTEGER | 1 = elasticity endpoint already attempted |
| `dielectric_fetched` | INTEGER | 1 = dielectric endpoint already attempted |

---

### `fetch.py` — Data Fetcher

Run once with `python fetch.py` to populate the database. Safe to re-run — skips compounds already cached.

| Name | Description |
|------|-------------|
| `CURATED` | Dict of 23 hand-picked mp-ids → category tag lists covering all 6 compound categories. |
| `CATEGORY_QUERIES` | List of (tag, search_kwargs, max_results) tuples for bulk category sweeps using MP property filters. |
| `FIELDS` | List of API field names requested from the Materials Project summary endpoint. |
| `extract_and_store(doc, tags)` | Extracts all relevant fields from an mp-api document object and writes them to the local database via `upsert`. |
| `_serialize_decomp(raw)` | Converts `DecompositionProduct` pydantic objects to plain JSON-serializable dicts. |
| `fetch_by_ids(mpr, id_tag_map)` | Fetches a specific set of mp-ids from the API and stores them; skips any already in the database. |
| `fetch_category(mpr, tag, kwargs, max_results)` | Bulk-fetches compounds matching a property filter query, up to max_results new compounds. |
| `refresh_extended_fields(mpr)` | Re-fetches extended fields (CBM, VBM, ordering, elements, etc.) for existing DB records that are missing them, without re-downloading 3D structures. |
| `fetch_elasticity(mpr)` | Fetches mechanical properties from the MP elasticity endpoint for all DB compounds not yet attempted; handles the `ThermalConductivity` pydantic object by averaging Clarke and Cahill estimates. |
| `fetch_dielectric(mpr)` | Fetches dielectric/optical properties from the MP dielectric endpoint for all DB compounds not yet attempted. |
| `main()` | Runs the full fetch pipeline: curated IDs → category sweeps → extended field refresh → elasticity → dielectric. |

---

### `compounds.py` — Compound Catalog

Defines the `COMPOUNDS` dict: a nested structure of `{ category → { display_name → data_dict } }` for the 23 curated compounds shown in the sidebar.

Each compound entry contains:
- `mp_id` — Materials Project identifier
- `formula` — Display formula with Unicode subscripts
- `crystal_system` / `space_group` — Crystallographic classification
- `key_props` — Dict of 3–4 notable properties with units
- `why_it_works` — 3–5 sentence plain-English explanation of structure–property relationship
- `accent` — Hex color used for the 3D viewer unit cell outline and chart highlight

**Categories:** Strong Magnets · Perovskites · Semiconductors · Space Elevator Candidates · Re-entry & Thermal Shield Materials (UHTCs) · Superconductors

---

### `pubchem.py` — PubChem Cross-Reference

Fetches experimentally measured chemical properties from the [PubChem](https://pubchem.ncbi.nlm.nih.gov) REST API to complement Materials Project's computed data.

| Function | Description |
|----------|-------------|
| `lookup(formula, name)` | Tries to find a compound in PubChem by formula, then by name; returns a flat property dict or None. |
| `_fetch_props(endpoint)` | Makes a raw GET request to the PubChem property API and returns the first result's property dict. |
| `_get_cas(cid)` | Fetches synonyms for a PubChem CID and extracts the CAS registry number using a regex pattern. |
| `format_prop(data, key, unit)` | Returns a formatted property string from a PubChem result dict, or None if the property is missing. |

**Properties fetched:** Molecular weight, melting point, boiling point, flash point, IUPAC name, InChI, InChIKey, canonical SMILES, CAS number.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Zero-scroll layout** | Streamlit header hidden; all panels use fixed-height `overflow-y:auto` containers so nothing on the page scrolls. |
| **3D Crystal Viewer** | Uses 3Dmol.js via a CDN-loaded iframe; auto-supercells small structures; spinning ball-and-stick with accent-colored unit cell outline. |
| **XRD Simulation** | CuKα X-ray diffraction pattern computed with pymatgen's `XRDCalculator`; handles hexagonal 4-index Miller-Bravais notation. |
| **Percentile Rank Bars** | Each property card shows a color-coded bar and "Top X% of N compounds" label, with rank direction inverted for lower-is-better properties. |
| **Position Chart** | Scatter of all DB compounds with the selected compound shown as a colored ★; axes auto-selected by compound category; filterable by crystal system or category. |
| **Ashby Charts** | Full material-selection scatter with log/linear axes and color grouping; good for comparing E vs ρ (space elevator), ε vs bandgap (plasma shielding), etc. |
| **Property Popovers** | ℹ buttons above each panel column open Streamlit popovers with detailed property explanations. |
| **PubChem Integration** | Experimental melting/boiling points and CAS numbers fetched and cached per compound. |
| **Local SQLite cache** | All data stored in `matsci.db`; app never hits the live API for already-fetched compounds. |

---

## Running fetch.py

```bash
python fetch.py
```

The fetcher runs five sequential steps:

1. **Curated IDs** — fetches 23 hand-picked compounds by exact mp-id
2. **Category sweeps** — bulk-fetches magnets, semiconductors, and perovskites by property filters
3. **Extended field refresh** — fills in any missing CBM/VBM/ordering fields for existing records
4. **Elasticity** — fetches mechanical data (only ~13k of 150k MP compounds have this)
5. **Dielectric** — fetches optical/dielectric data (~7k compounds have this)

After step 1 completes you can already run the app. Steps 4–5 can take 30–60 minutes for a large database.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `mp-api` | Materials Project Python client |
| `pymatgen` | Crystal structure parsing, XRD simulation, CIF export |
| `plotly` | Interactive charts (Ashby, XRD, position scatter) |
| `python-dotenv` | Load `MP_API_KEY` from `.env` file |
| `requests` | PubChem REST API calls |
| `sqlite3` | Built-in Python — local database (no install needed) |

---

## Data Sources

- **[Materials Project](https://materialsproject.org)** — DFT-computed crystal structures, electronic, mechanical, and dielectric properties for ~160,000 compounds (as of 2025). Requires a free API key.
- **[PubChem](https://pubchem.ncbi.nlm.nih.gov)** — NCBI's open chemistry database with experimentally measured thermal and chemical properties. No key required.
