# fetch.py
# Bulk data fetcher — run this ONCE to populate the local database.
#
# What it does:
#   1. Fetches our 9 curated compounds by MP ID (always first)
#   2. Then bulk-fetches broader categories using property filters
#   3. Skips anything already in the database (safe to re-run)
#   4. Rate-limits between batches to be a good API citizen
#
# Usage:
#   python fetch.py
#
# After this runs, the app reads from matsci.db and never needs the API again
# for those compounds. Add new compounds to CURATED_IDS or tweak CATEGORY_QUERIES
# to expand the database.

import os
import time
from dotenv import load_dotenv
from mp_api.client import MPRester

import json
from db import (init_db, upsert, has_material, stats, get_conn,
                save_elasticity, save_dielectric)

load_dotenv()
API_KEY = os.environ.get("MP_API_KEY")

# ── Fields to request from the API ───────────────────────────────────────────
# We only ask for what we actually use — smaller response = faster + polite.
FIELDS = [
    "material_id",
    "formula_pretty",
    "formula_anonymous",
    "symmetry",                        # contains crystal_system + space_group
    "band_gap",
    "cbm",
    "vbm",
    "is_gap_direct",
    "total_magnetization",
    "ordering",                        # magnetic ordering: FM, AFM, FiM, NM
    "num_magnetic_sites",
    "formation_energy_per_atom",
    "energy_above_hull",
    "decomposes_to",
    "nsites",
    "volume",
    "density",
    "density_atomic",
    "nelements",
    "elements",
    "chemsys",
    "theoretical",
    "database_IDs",                    # contains ICSD IDs and others
    "structure",
]

# ── Our 9 hand-curated compounds (always fetch these) ─────────────────────────
CURATED = {
    # Strong Magnets
    "mp-5182":    ["magnet"],         # Nd2Fe14B  (corrected from mp-22233)
    "mp-13":      ["magnet"],         # Fe
    "mp-1429":    ["magnet"],         # SmCo5    (corrected from mp-974689)
    # Perovskites
    "mp-2998":    ["perovskite"],     # BaTiO3
    "mp-5229":    ["perovskite"],     # SrTiO3
    "mp-567629":  ["perovskite"],     # CsPbBr3
    # Semiconductors
    "mp-149":     ["semiconductor"],  # Si
    "mp-2534":    ["semiconductor"],  # GaAs
    "mp-2657":    ["semiconductor"],  # TiO2 rutile
    # Space Elevator Candidates
    "mp-66":      ["space_elevator"], # Diamond (C)
    "mp-13150":   ["space_elevator"], # h-BN  (corrected from mp-984)
    "mp-7631":    ["space_elevator"], # SiC cubic  (corrected from mp-8062)
    "mp-631":     ["space_elevator"], # TiC
    "mp-1143":    ["space_elevator"], # Al2O3 corundum
    # Re-entry / UHTC
    "mp-1472":    ["uhtc"],           # ZrB2  (corrected from mp-1994)
    "mp-1994":    ["uhtc"],           # HfB2  (corrected from mp-2192)
    "mp-1145":    ["uhtc"],           # TiB2  (corrected from mp-1992)
    "mp-1014307": ["uhtc"],           # ZrC   (corrected from mp-2574)
    "mp-776404":  ["uhtc"],           # ZrO2  (corrected from mp-2858)
    # Superconductors
    "mp-2739273": ["superconductor"], # Nb    (corrected from mp-75)
    "mp-763":     ["superconductor"], # MgB2
    "mp-20483":   ["superconductor"], # Pb
    "mp-2701":    ["superconductor"], # NbN   (corrected from mp-20056)
    # Battery
    "mp-22526":   ["battery"],        # LiCoO2
    "mp-19017":   ["battery"],        # LiFePO4
    "mp-25338":   ["battery"],        # LiMn2O4
    "mp-776745":  ["battery"],        # Li4Ti5O12
    # Catalysts
    "mp-126":     ["catalyst"],       # Pt
    "mp-20194":   ["catalyst"],       # CeO2
    "mp-1023924": ["catalyst"],       # MoS2
    "mp-19770":   ["catalyst"],       # Fe2O3
    # Thermoelectrics
    "mp-34202":   ["thermoelectric"], # Bi2Te3
    "mp-19717":   ["thermoelectric"], # PbTe
    "mp-2490":    ["thermoelectric"], # CoSb3
    # Topological Insulators
    "mp-541837":  ["topological"],    # Bi2Se3
    "mp-29227":   ["topological"],    # Bi2Te2Se
    "mp-1883":    ["topological"],    # SnTe
}

# ── Broader category queries ──────────────────────────────────────────────────
# Each entry is: (tag_label, search_kwargs, max_results)
# Keep max_results modest — this is a learning tool, not a full MP mirror.
# energy_above_hull near 0 means stable/synthesizable compounds only.
CATEGORY_QUERIES = [
    (
        "magnet",
        dict(
            total_magnetization=(2.0, None),   # clearly magnetic
            energy_above_hull=(0, 0.05),       # stable
            nsites=(1, 20),                    # not too complex
        ),
        300,
    ),
    (
        "semiconductor",
        dict(
            band_gap=(0.5, 3.5),               # useful solar/electronics range
            energy_above_hull=(0, 0.02),       # very stable
            nsites=(1, 8),                     # simple structures
        ),
        400,
    ),
    # Perovskites split by crystal system (API only allows ≤2 values per filter)
    (
        "perovskite",
        dict(nsites=(5, 20), energy_above_hull=(0, 0.1), crystal_system=["cubic", "tetragonal"]),
        150,
    ),
    (
        "perovskite",
        dict(nsites=(5, 20), energy_above_hull=(0, 0.1), crystal_system=["orthorhombic", "trigonal"]),
        150,
    ),
]

PAUSE_EVERY       = 100   # pause after this many stored records
PAUSE_SECS        = 1.0   # seconds to pause (be polite to MP servers)
RATE_LIMIT_DELAY  = 1.0   # alias used in refresh functions


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_decomp(raw):
    """Convert DecompositionProduct objects to plain dicts for JSON storage."""
    if not raw:
        return None
    try:
        return [{"formula": str(d.formula), "amount": float(d.amount)} for d in raw]
    except Exception:
        return None


def extract_and_store(doc, tags: list[str]):
    """Pull fields from an mp-api document and write to local DB."""
    sym = doc.symmetry

    # Extract ICSD IDs from the database_IDs cross-reference field
    db_ids = getattr(doc, "database_IDs", None) or {}
    icsd_ids = db_ids.get("icsd", []) if isinstance(db_ids, dict) else []

    # Magnetic ordering as a plain string
    ordering = None
    if hasattr(doc, "ordering") and doc.ordering:
        ordering = str(doc.ordering.value) if hasattr(doc.ordering, "value") else str(doc.ordering)

    # Elements as a list of strings
    elements = [str(e) for e in doc.elements] if doc.elements else None

    upsert(
        mp_id              = doc.material_id,
        formula            = doc.formula_pretty,
        crystal_system     = sym.crystal_system.value if sym else None,
        space_group        = sym.symbol if sym else None,
        bandgap            = doc.band_gap,
        cbm                = getattr(doc, "cbm", None),
        vbm                = getattr(doc, "vbm", None),
        is_direct          = doc.is_gap_direct,
        magnetization      = doc.total_magnetization,
        ordering           = ordering,
        num_magnetic_sites = getattr(doc, "num_magnetic_sites", None),
        formation_e        = doc.formation_energy_per_atom,
        hull_e             = doc.energy_above_hull,
        decomposes_to      = _serialize_decomp(getattr(doc, "decomposes_to", None)),
        nsites             = doc.nsites,
        volume             = doc.volume,
        density            = doc.density,
        density_atomic     = getattr(doc, "density_atomic", None),
        nelements          = getattr(doc, "nelements", None),
        elements           = elements,
        chemsys            = getattr(doc, "chemsys", None),
        theoretical        = getattr(doc, "theoretical", None),
        icsd_ids           = icsd_ids,
        formula_anonymous  = getattr(doc, "formula_anonymous", None),
        structure          = doc.structure,
        tags               = tags,
    )


def fetch_by_ids(mpr, id_tag_map: dict):
    """Fetch specific MP IDs (our curated set)."""
    print("\n── Curated compounds ────────────────────────────────")
    ids_needed = [mid for mid in id_tag_map if not has_material(mid)]

    if not ids_needed:
        print("  All curated compounds already in database. Skipping.")
        return

    print(f"  Fetching {len(ids_needed)} compound(s)...")
    docs = mpr.materials.summary.search(
        material_ids=ids_needed,
        fields=FIELDS,
    )
    for doc in docs:
        extract_and_store(doc, id_tag_map[doc.material_id])
        print(f"  Stored {doc.material_id:12s}  {doc.formula_pretty}")


def fetch_category(mpr, tag: str, kwargs: dict, max_results: int):
    """Bulk-fetch a category and store results."""
    print(f"\n── Category: {tag} (max {max_results}) ──────────────────────────")

    docs = mpr.materials.summary.search(fields=FIELDS, **kwargs)
    total_found = len(docs)
    print(f"  API returned {total_found} compounds")

    stored = 0
    skipped = 0

    for i, doc in enumerate(docs):
        if stored >= max_results:
            break

        if has_material(doc.material_id):
            skipped += 1
            continue

        try:
            extract_and_store(doc, [tag])
            stored += 1
            print(f"  [{stored:>3}/{max_results}] {doc.material_id:12s}  {doc.formula_pretty}")
        except Exception as e:
            print(f"  Warning: could not store {doc.material_id}: {e}")

        # Rate limiting: pause periodically
        if stored % PAUSE_EVERY == 0 and stored > 0:
            print(f"  Pausing {PAUSE_SECS}s (rate limit courtesy)...")
            time.sleep(PAUSE_SECS)

    print(f"  Done: {stored} new, {skipped} already cached")


# ── Main ──────────────────────────────────────────────────────────────────────

FIELDS_NO_STRUCT = [f for f in FIELDS if f != "structure"]


def refresh_extended_fields(mpr):
    """
    Update existing DB records that are missing the extended fields
    (cbm, vbm, ordering, elements, etc.) added in the schema expansion.
    Re-uses existing structure data — no re-download of 3D structures.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT mp_id, tags, structure_json FROM materials WHERE cbm IS NULL"
        ).fetchall()

    if not rows:
        print("\n  All compounds already have extended fields. Nothing to refresh.")
        return

    print(f"\n── Refreshing extended fields for {len(rows)} existing compounds ──")

    BATCH = 100
    for i in range(0, len(rows), BATCH):
        batch_rows = rows[i: i + BATCH]
        batch_ids  = [r[0] for r in batch_rows]
        struct_map = {r[0]: r[2] for r in batch_rows}
        tag_map    = {r[0]: json.loads(r[1]) if r[1] else [] for r in batch_rows}

        try:
            docs = mpr.materials.summary.search(
                material_ids=batch_ids,
                fields=FIELDS_NO_STRUCT,
            )
        except Exception as e:
            print(f"  Batch {i // BATCH + 1} error: {e}")
            continue

        for doc in docs:
            mid  = doc.material_id
            sym  = doc.symmetry
            db_ids   = getattr(doc, "database_IDs", None) or {}
            icsd_ids = db_ids.get("icsd", []) if isinstance(db_ids, dict) else []
            ordering = None
            if hasattr(doc, "ordering") and doc.ordering:
                ordering = str(doc.ordering.value) if hasattr(doc.ordering, "value") else str(doc.ordering)
            elements = [str(e) for e in doc.elements] if doc.elements else None

            # Restore existing structure (don't re-download)
            struct_json = struct_map.get(mid)
            structure   = None
            if struct_json:
                try:
                    from pymatgen.core import Structure as _S
                    structure = _S.from_dict(json.loads(struct_json))
                except Exception:
                    pass

            upsert(
                mp_id=mid, formula=doc.formula_pretty,
                crystal_system=sym.crystal_system.value if sym else None,
                space_group=sym.symbol if sym else None,
                bandgap=doc.band_gap,
                cbm=getattr(doc, "cbm", None),
                vbm=getattr(doc, "vbm", None),
                is_direct=doc.is_gap_direct,
                magnetization=doc.total_magnetization,
                ordering=ordering,
                num_magnetic_sites=getattr(doc, "num_magnetic_sites", None),
                formation_e=doc.formation_energy_per_atom,
                hull_e=doc.energy_above_hull,
                decomposes_to=_serialize_decomp(getattr(doc, "decomposes_to", None)),
                nsites=doc.nsites, volume=doc.volume, density=doc.density,
                density_atomic=getattr(doc, "density_atomic", None),
                nelements=getattr(doc, "nelements", None),
                elements=elements,
                chemsys=getattr(doc, "chemsys", None),
                theoretical=getattr(doc, "theoretical", None),
                icsd_ids=icsd_ids,
                formula_anonymous=getattr(doc, "formula_anonymous", None),
                structure=structure,
                tags=tag_map.get(mid, []),
            )

        print(f"  Batch {i // BATCH + 1}/{(len(rows) - 1) // BATCH + 1} done "
              f"({min(i + BATCH, len(rows))}/{len(rows)} compounds)")
        time.sleep(RATE_LIMIT_DELAY)

    print("  Refresh complete.")


def fetch_elasticity(mpr):
    """
    Fetch mechanical properties for all DB compounds that haven't been attempted yet.
    Uses the MP elasticity endpoint — only ~13k of 150k compounds have this data,
    so most will return nothing (that's fine and expected).
    """
    with get_conn() as conn:
        ids = [r[0] for r in conn.execute(
            "SELECT mp_id FROM materials WHERE elastic_fetched IS NULL OR elastic_fetched = 0"
        ).fetchall()]

    if not ids:
        print("\n  All compounds already have elasticity fetch attempted.")
        return

    print(f"\n── Fetching mechanical/elasticity data ({len(ids)} compounds to try) ──")
    found = 0
    BATCH = 100

    for i in range(0, len(ids), BATCH):
        batch = ids[i: i + BATCH]
        try:
            docs = mpr.materials.elasticity.search(
                material_ids=batch,
                fields=["material_id", "bulk_modulus", "shear_modulus",
                        "youngs_modulus", "universal_anisotropy", "homogeneous_poisson",
                        "thermal_conductivity", "debye_temperature"],
            )
            fetched_ids = set()
            for doc in docs:
                mid = doc.material_id
                fetched_ids.add(mid)
                # bulk_modulus / shear_modulus are objects with .voigt attribute (already in GPa)
                B = doc.bulk_modulus.voigt  if doc.bulk_modulus  else None
                G = doc.shear_modulus.voigt if doc.shear_modulus else None
                # youngs_modulus is a float in GPa
                E = getattr(doc, "youngs_modulus", None)
                if E is None and B and G:
                    E = (9 * B * G) / (3 * B + G)  # compute if not provided
                # thermal_conductivity is a ThermalConductivity object with
                # .clarke and .cahill attributes (two estimation methods, W/m·K).
                # We store the average of both as our single value.
                tc_raw = getattr(doc, "thermal_conductivity", None)
                if tc_raw is not None:
                    try:
                        tc = float(tc_raw)  # works if it ever becomes a plain float
                    except (TypeError, ValueError):
                        clarke = getattr(tc_raw, "clarke", None)
                        cahill = getattr(tc_raw, "cahill", None)
                        vals = [v for v in (clarke, cahill) if v is not None]
                        tc = sum(vals) / len(vals) if vals else None
                else:
                    tc = None
                save_elasticity(
                    mp_id=mid, k_voigt=B, g_voigt=G, young_modulus=E,
                    poisson_ratio=doc.homogeneous_poisson,
                    universal_anisotropy=doc.universal_anisotropy,
                    thermal_conductivity=tc,
                    debye_temperature=getattr(doc, "debye_temperature", None),
                )
                found += 1

            # Mark all batch IDs as attempted (even those with no elasticity data)
            for mid in batch:
                if mid not in fetched_ids:
                    save_elasticity(mid, None, None, None, None, None)

        except Exception as e:
            print(f"  Batch {i // BATCH + 1} error: {e}")

        if (i // BATCH + 1) % 5 == 0:
            print(f"  Progress: {min(i + BATCH, len(ids))}/{len(ids)} attempted, {found} with data")
        time.sleep(RATE_LIMIT_DELAY)

    print(f"  Done — found elasticity data for {found} compounds")


def fetch_dielectric(mpr):
    """
    Fetch dielectric/optical properties for all DB compounds not yet attempted.
    MP has ~7k compounds with this data.
    """
    with get_conn() as conn:
        ids = [r[0] for r in conn.execute(
            "SELECT mp_id FROM materials WHERE dielectric_fetched IS NULL OR dielectric_fetched = 0"
        ).fetchall()]

    if not ids:
        print("\n  All compounds already have dielectric fetch attempted.")
        return

    print(f"\n── Fetching dielectric/optical data ({len(ids)} compounds to try) ──")
    found = 0
    BATCH = 100

    for i in range(0, len(ids), BATCH):
        batch = ids[i: i + BATCH]
        try:
            docs = mpr.materials.dielectric.search(
                material_ids=batch,
                fields=["material_id", "e_total", "e_ionic", "e_electronic", "n"],
            )
            fetched_ids = set()
            for doc in docs:
                mid = doc.material_id
                fetched_ids.add(mid)
                # Cap wildly large values (metals have unphysical static dielectric)
                e_tot = doc.e_total if (doc.e_total and doc.e_total < 10000) else None
                save_dielectric(
                    mp_id=mid,
                    e_total=e_tot,
                    e_ionic=doc.e_ionic,
                    e_electronic=doc.e_electronic,
                    refractive_index=doc.n,
                )
                found += 1

            for mid in batch:
                if mid not in fetched_ids:
                    save_dielectric(mid, None, None, None, None)

        except Exception as e:
            print(f"  Batch {i // BATCH + 1} error: {e}")

        if (i // BATCH + 1) % 5 == 0:
            print(f"  Progress: {min(i + BATCH, len(ids))}/{len(ids)} attempted, {found} with data")
        time.sleep(RATE_LIMIT_DELAY)

    print(f"  Done — found dielectric data for {found} compounds")


def main():
    if not API_KEY:
        print("Error: MP_API_KEY not found. Make sure .env exists with your key.")
        return

    print("MatSci Explorer — Database Fetcher")
    print("=" * 45)

    init_db()

    before = stats()
    print(f"Database before fetch: {before['total']} compounds")

    with MPRester(API_KEY) as mpr:
        # Step 1: Always get our curated hand-picked compounds first
        fetch_by_ids(mpr, CURATED)

        # Step 2: Broad category sweeps
        for tag, kwargs, max_n in CATEGORY_QUERIES:
            try:
                fetch_category(mpr, tag, kwargs, max_n)
            except Exception as e:
                print(f"\nError fetching category '{tag}': {e}")
                print("Continuing with next category...")

        # Step 3: Fill extended fields for any compounds missing them
        refresh_extended_fields(mpr)

        # Step 4: Mechanical properties (elasticity endpoint)
        fetch_elasticity(mpr)

        # Step 5: Dielectric / optical properties
        fetch_dielectric(mpr)

    after = stats()
    new_count = after['total'] - before['total']
    print(f"\n{'='*45}")
    print(f"Fetch complete!")
    print(f"  Added : {new_count} new compounds")
    print(f"  Total : {after['total']} compounds in database")
    print(f"  With structures : {after['with_structure']}")
    print(f"\nThe app will now serve all fetched compounds from local storage.")
    print(f"Database file: matsci.db")


if __name__ == "__main__":
    main()
