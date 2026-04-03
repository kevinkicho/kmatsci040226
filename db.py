# db.py
# Local SQLite database for MatSci Explorer.
# All Materials Project data is stored here after the first fetch,
# so the app never needs to hit the API again for known compounds.

import sqlite3
import json
import os
from datetime import datetime
from pymatgen.core import Structure

DB_PATH = os.path.join(os.path.dirname(__file__), "matsci.db")


def get_conn():
    """Open a connection to the local database."""
    return sqlite3.connect(DB_PATH)


def migrate_db():
    """
    Add new columns to existing database without losing data.
    Safe to call on any version of the DB — skips columns that already exist.
    """
    new_columns = [
        ("cbm",               "REAL"),    # conduction band minimum (eV)
        ("vbm",               "REAL"),    # valence band maximum (eV)
        ("ordering",          "TEXT"),    # magnetic: FM, AFM, FiM, NM, Unknown
        ("num_magnetic_sites","INTEGER"),
        ("theoretical",       "INTEGER"), # 1=only computed, 0=experimentally observed
        ("formula_anonymous", "TEXT"),    # e.g. "AB2C3" — useful for finding same topology
        ("nelements",         "INTEGER"),
        ("elements",          "TEXT"),    # JSON array e.g. ["Fe","Nd","B"]
        ("chemsys",           "TEXT"),    # e.g. "B-Fe-Nd"
        ("icsd_ids",          "TEXT"),    # JSON array of ICSD IDs
        ("decomposes_to",     "TEXT"),    # JSON — what it breaks into if unstable
        ("density_atomic",    "REAL"),    # atoms/Å³
        ("pubchem_json",      "TEXT"),    # cached PubChem lookup result
        ("pubchem_fetched_at","TEXT"),
        # Mechanical / elasticity (from MP elasticity endpoint)
        ("k_voigt",            "REAL"),   # bulk modulus, GPa
        ("g_voigt",            "REAL"),   # shear modulus, GPa
        ("young_modulus",      "REAL"),   # Young's modulus, GPa (computed: E=9BG/(3B+G))
        ("poisson_ratio",      "REAL"),   # Poisson's ratio (dimensionless)
        ("universal_anisotropy","REAL"),  # elastic anisotropy index
        ("elastic_fetched",    "INTEGER"),# 1=attempted, prevents repeated API calls
        # Thermal (from MP elasticity endpoint bonus fields)
        ("thermal_conductivity","REAL"),  # W/m·K
        ("debye_temperature",  "REAL"),   # K
        # Dielectric / optical (from MP dielectric endpoint)
        ("e_total",            "REAL"),   # total static dielectric constant
        ("e_ionic",            "REAL"),   # ionic contribution
        ("e_electronic",       "REAL"),   # electronic contribution
        ("refractive_index",   "REAL"),   # n = sqrt(e_electronic)
        ("dielectric_fetched", "INTEGER"),# 1=attempted
    ]
    with get_conn() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(materials)").fetchall()}
        added = []
        for col, typ in new_columns:
            if col not in existing:
                conn.execute(f"ALTER TABLE materials ADD COLUMN {col} {typ}")
                added.append(col)
        conn.commit()
    if added:
        print(f"  DB migration: added columns {added}")


def init_db():
    """Create tables if they don't already exist, then run any pending migrations."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_notes (
                mp_id  TEXT PRIMARY KEY,
                note   TEXT NOT NULL DEFAULT '',
                ts     TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                mp_id                      TEXT PRIMARY KEY,
                formula                    TEXT,
                crystal_system             TEXT,
                space_group                TEXT,
                bandgap                    REAL,
                is_direct_gap              INTEGER,   -- 1=direct, 0=indirect, NULL=unknown
                total_magnetization        REAL,
                formation_energy_per_atom  REAL,
                energy_above_hull          REAL,      -- stability: 0 = perfectly stable
                nsites                     INTEGER,   -- atoms per unit cell
                volume                     REAL,      -- Å³
                density                    REAL,      -- g/cm³
                structure_json             TEXT,      -- full pymatgen Structure as JSON
                tags                       TEXT,      -- JSON array e.g. ["magnet","perovskite"]
                fetched_at                 TEXT       -- ISO timestamp
            )
        """)
        conn.commit()
    migrate_db()  # add any new columns to existing DBs
    print(f"Database ready at: {DB_PATH}")


def upsert(mp_id, formula, crystal_system, space_group,
           bandgap, is_direct, magnetization, formation_e,
           hull_e, nsites, volume, density, structure, tags,
           # extended fields (all optional)
           cbm=None, vbm=None, ordering=None, num_magnetic_sites=None,
           theoretical=None, formula_anonymous=None, nelements=None,
           elements=None, chemsys=None, icsd_ids=None, decomposes_to=None,
           density_atomic=None):
    """Insert or update a material record (extended schema)."""
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO materials
            (mp_id, formula, crystal_system, space_group,
             bandgap, is_direct_gap, total_magnetization,
             formation_energy_per_atom, energy_above_hull,
             nsites, volume, density, structure_json, tags, fetched_at,
             cbm, vbm, ordering, num_magnetic_sites, theoretical,
             formula_anonymous, nelements, elements, chemsys,
             icsd_ids, decomposes_to, density_atomic)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            mp_id, formula, crystal_system, space_group,
            bandgap,
            int(is_direct) if is_direct is not None else None,
            magnetization, formation_e, hull_e,
            nsites, volume, density,
            json.dumps(structure.as_dict()) if structure else None,
            json.dumps(tags or []),
            datetime.utcnow().isoformat(),
            cbm, vbm, ordering, num_magnetic_sites,
            int(theoretical) if theoretical is not None else None,
            formula_anonymous, nelements,
            json.dumps(elements) if elements else None,
            chemsys,
            json.dumps(icsd_ids) if icsd_ids else None,
            json.dumps(decomposes_to) if decomposes_to else None,
            density_atomic,
        ))
        conn.commit()


def save_pubchem(mp_id: str, data: dict):
    """Store a PubChem lookup result for a material."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE materials SET pubchem_json=?, pubchem_fetched_at=? WHERE mp_id=?",
            (json.dumps(data), datetime.utcnow().isoformat(), mp_id)
        )
        conn.commit()


def has_material(mp_id: str) -> bool:
    """Check if a material is already in the local database."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM materials WHERE mp_id=?", (mp_id,)
        ).fetchone()
    return row is not None


def get_structure(mp_id: str) -> Structure | None:
    """Load a pymatgen Structure from the local database."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT structure_json FROM materials WHERE mp_id=?", (mp_id,)
        ).fetchone()
    if row and row[0]:
        return Structure.from_dict(json.loads(row[0]))
    return None


def get_material_row(mp_id: str) -> dict | None:
    """Return all fields for one material as a dict."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM materials WHERE mp_id=?", (mp_id,)
        ).fetchone()
    return dict(row) if row else None


def search(
    crystal_system: str = None,
    min_bandgap: float = None,
    max_bandgap: float = None,
    min_magnetization: float = None,
    tag: str = None,
    limit: int = 200,
) -> list[dict]:
    """
    Query the local database by property filters.
    Returns a list of dicts, one per matching material.
    """
    query = "SELECT * FROM materials WHERE 1=1"
    params = []

    if crystal_system:
        query += " AND crystal_system = ?"
        params.append(crystal_system)
    if min_bandgap is not None:
        query += " AND bandgap >= ?"
        params.append(min_bandgap)
    if max_bandgap is not None:
        query += " AND bandgap <= ?"
        params.append(max_bandgap)
    if min_magnetization is not None:
        query += " AND total_magnetization >= ?"
        params.append(min_magnetization)
    if tag:
        query += " AND tags LIKE ?"
        params.append(f'%"{tag}"%')

    query += " ORDER BY formula LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def save_elasticity(mp_id: str, k_voigt: float, g_voigt: float,
                    young_modulus: float, poisson_ratio: float,
                    universal_anisotropy: float,
                    thermal_conductivity: float = None,
                    debye_temperature: float = None):
    """Store mechanical properties. Call even if values are None (sets elastic_fetched=1)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE materials SET k_voigt=?, g_voigt=?, young_modulus=?, "
            "poisson_ratio=?, universal_anisotropy=?, elastic_fetched=1, "
            "thermal_conductivity=?, debye_temperature=? WHERE mp_id=?",
            (k_voigt, g_voigt, young_modulus, poisson_ratio, universal_anisotropy,
             thermal_conductivity, debye_temperature, mp_id)
        )
        conn.commit()


def save_dielectric(mp_id: str, e_total: float, e_ionic: float,
                    e_electronic: float, refractive_index: float):
    """Store dielectric/optical properties. Call even if values are None (sets dielectric_fetched=1)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE materials SET e_total=?, e_ionic=?, e_electronic=?, "
            "refractive_index=?, dielectric_fetched=1 WHERE mp_id=?",
            (e_total, e_ionic, e_electronic, refractive_index, mp_id)
        )
        conn.commit()


def get_ashby_data(x_col: str, y_col: str, color_col: str = "crystal_system",
                   limit: int = 2000) -> list[dict]:
    """
    Query all compounds that have non-null values for both axis columns.
    Used by the Ashby chart view.
    """
    safe_cols = {
        "density", "young_modulus", "k_voigt", "g_voigt", "bandgap",
        "total_magnetization", "formation_energy_per_atom", "energy_above_hull",
        "e_total", "refractive_index", "poisson_ratio", "universal_anisotropy",
        "nsites", "nelements", "density_atomic", "volume",
        "thermal_conductivity", "debye_temperature",
    }
    if x_col not in safe_cols or y_col not in safe_cols:
        return []
    color_safe = {"crystal_system", "tags", "ordering", "theoretical"}
    c_col = color_col if color_col in color_safe else "crystal_system"
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT formula, mp_id, {x_col}, {y_col}, {c_col} "
            f"FROM materials WHERE {x_col} IS NOT NULL AND {y_col} IS NOT NULL "
            f"LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_position_data(x_col: str, y_col: str,
                      filter_mode: str = "All",
                      crystal_system: str = None,
                      tag: str = None,
                      limit: int = 3000) -> list[dict]:
    """Query compounds for the position/comparison scatter chart."""
    safe = {
        "density","young_modulus","k_voigt","g_voigt","bandgap",
        "total_magnetization","formation_energy_per_atom","energy_above_hull",
        "e_total","refractive_index","poisson_ratio","debye_temperature",
        "thermal_conductivity",
    }
    if x_col not in safe or y_col not in safe:
        return []
    query  = (f"SELECT mp_id, formula, {x_col}, {y_col}, crystal_system, tags "
              f"FROM materials WHERE {x_col} IS NOT NULL AND {y_col} IS NOT NULL")
    params: list = []
    if filter_mode == "crystal_system" and crystal_system:
        query += " AND crystal_system = ?"; params.append(crystal_system)
    elif filter_mode == "category" and tag:
        query += " AND tags LIKE ?"; params.append(f'%"{tag}"%')
    query += " LIMIT ?"; params.append(limit)
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_note(mp_id: str) -> str:
    """Return the user's saved note for a compound, or '' if none."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT note FROM user_notes WHERE mp_id=?", (mp_id,)
        ).fetchone()
    return row[0] if row else ""


def save_note(mp_id: str, note: str):
    """Upsert a user note for a compound."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_notes (mp_id, note, ts) VALUES (?,?,?) "
            "ON CONFLICT(mp_id) DO UPDATE SET note=excluded.note, ts=excluded.ts",
            (mp_id, note.strip(), datetime.utcnow().isoformat())
        )
        conn.commit()


def stats() -> dict:
    """Return basic counts for a status summary."""
    with get_conn() as conn:
        total    = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
        with_bg  = conn.execute("SELECT COUNT(*) FROM materials WHERE bandgap IS NOT NULL").fetchone()[0]
        with_st  = conn.execute("SELECT COUNT(*) FROM materials WHERE structure_json IS NOT NULL").fetchone()[0]
        with_mec = conn.execute("SELECT COUNT(*) FROM materials WHERE k_voigt IS NOT NULL").fetchone()[0]
        with_die = conn.execute("SELECT COUNT(*) FROM materials WHERE e_total IS NOT NULL").fetchone()[0]
    return {
        "total": total, "with_bandgap": with_bg,
        "with_structure": with_st, "with_elasticity": with_mec,
        "with_dielectric": with_die,
    }
