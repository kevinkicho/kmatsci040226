# MatSci Explorer

A personal materials science learning dashboard that connects crystal structure to material properties.
Built with Streamlit, the Materials Project API, and pymatgen.

---

## What it does

MatSci Explorer lets you browse 25 curated compounds across 8 categories, visualize their crystal structures in 3D, explore key physical properties, and understand *why* a material's structure determines its behavior.

**Categories:** Strong Magnets · Perovskites · Semiconductors · Space Elevator Candidates · Re-entry / Thermal Shield · Superconductors · Battery Materials · Catalysts

---

## Features

### Crystal viewer
- Interactive 3D rotating structure (py3Dmol, WebGL) with accent-colored unit cell outline
- Lattice parameters and site count
- "Why this structure → this property" — hover to reveal a plain-language explanation per compound

### Property panels (2×2 grid)
- **Electronic & Magnetic** — band gap, direct/indirect, CBM/VBM, magnetization, magnetic ordering
- **Mechanical & Thermal** — Young's modulus, bulk/shear modulus, Poisson ratio, anisotropy, Debye temperature, thermal conductivity
- **Dielectric & Optical** — total/ionic/electronic dielectric constant, refractive index
- **Stability & Physical** — hull energy, formation energy, density, volume, ICSD IDs
- Every property label has a rich hover tooltip with a colored scale and plain-English description
- Percentile rank bars vs 6,800+ Materials Project compounds in the local database

### Navigation
- Sidebar 2-column category dropdown grid for fast compound switching
- Full-text search by formula or mp-id
- Property filter expander — narrow by bandgap, density, Young's modulus, magnetization, and more
- Browser back/forward support — URL query param `?mp=mp-xxxx` is set on every navigation
- Click any point in the position chart to navigate directly to that compound

### Comparison mode
- Pin a compound, then pick a second — side-by-side 3D viewers, mirrored XRD overlay, color-coded delta table

### Ashby Charts
- Scatter any two properties against each other; color by crystal system, magnetic ordering, or theoretical flag

### XRD patterns
- Simulated Cu Kα powder diffraction (pymatgen `XRDCalculator`)

### Notes
- "Add note" button per compound — write and save personal observations; stored locally in SQLite

### Wikipedia integration
- Brief summary and external link fetched from Wikipedia and cached locally

---

## Installation

**Prerequisites:** Python 3.11+, a free [Materials Project API key](https://materialsproject.org/api)

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

## Project structure

```
kmatsci040226/
├── app.py           # Streamlit dashboard (UI, charts, dialogs)
├── compounds.py     # Curated compound catalog with mp_ids and explanations
├── db.py            # SQLite database layer (schema, queries, migrations)
├── fetch.py         # One-time bulk fetcher from Materials Project API
├── pubchem.py       # PubChem cross-reference for experimental properties
├── wikipedia.py     # Wikipedia summary fetcher with local cache
├── matsci.db        # SQLite database (auto-created by fetch.py)
├── cache/           # JSON cache for structures and Wikipedia pages
└── .env             # API key (MP_API_KEY=...)
```

---

## Running fetch.py

```bash
python fetch.py
```

Runs five sequential steps:

1. **Curated IDs** — fetches the hand-picked compounds by exact mp-id
2. **Category sweeps** — bulk-fetches magnets, semiconductors, and perovskites by property filters
3. **Extended field refresh** — fills in missing CBM/VBM/ordering fields for existing records
4. **Elasticity** — fetches mechanical data from the MP elasticity endpoint
5. **Dielectric** — fetches optical/dielectric data

After step 1 completes you can already run the app. Steps 4–5 can take 30–60 minutes for a large database.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `mp-api` | Materials Project Python client |
| `pymatgen` | Crystal structure parsing, XRD simulation |
| `plotly` | Interactive charts (Ashby, XRD, position scatter) |
| `python-dotenv` | Load `MP_API_KEY` from `.env` file |
| `requests` | PubChem REST API calls |
| `sqlite3` | Built-in Python — local database (no install needed) |

---

## Data sources

- **[Materials Project](https://materialsproject.org)** — DFT-computed crystal structures, electronic, mechanical, and dielectric properties. Requires a free API key.
- **[PubChem](https://pubchem.ncbi.nlm.nih.gov)** — Open chemistry database with experimentally measured thermal and chemical properties. No key required.
- **[Wikipedia](https://en.wikipedia.org)** — REST v1 summary API for compound background text. No key required.

---

## License

Personal learning project — not intended for production or commercial use.
