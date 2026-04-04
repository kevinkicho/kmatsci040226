"""Tests for db.py — all use an isolated temp database."""
import pytest


def _insert(db, mp_id="mp-1", formula="Fe", bandgap=0.0, crystal_system="cubic",
            density=7.87, nsites=2, volume=23.0, magnetization=2.2,
            formation_e=-0.5, hull_e=0.0):
    db.upsert(
        mp_id, formula, crystal_system, "Im-3m",
        bandgap, False, magnetization, formation_e,
        hull_e, nsites, volume, density, None, [],
        nelements=1, elements=["Fe"], chemsys="Fe",
    )


# ── has_material ──────────────────────────────────────────────────────────────

def test_has_material_missing(test_db):
    assert test_db.has_material("mp-999") is False


def test_has_material_present(test_db):
    _insert(test_db)
    assert test_db.has_material("mp-1") is True


# ── upsert / get_material_row ─────────────────────────────────────────────────

def test_upsert_creates_row(test_db):
    _insert(test_db, mp_id="mp-2", formula="Si", bandgap=1.1, density=2.33)
    row = test_db.get_material_row("mp-2")
    assert row is not None
    assert row["formula"] == "Si"
    assert row["bandgap"] == pytest.approx(1.1)
    assert row["density"] == pytest.approx(2.33)


def test_upsert_replaces_row(test_db):
    _insert(test_db, mp_id="mp-3", bandgap=0.0)
    _insert(test_db, mp_id="mp-3", bandgap=2.5)
    row = test_db.get_material_row("mp-3")
    assert row["bandgap"] == pytest.approx(2.5)


def test_get_material_row_missing(test_db):
    assert test_db.get_material_row("mp-404") is None


# ── search ────────────────────────────────────────────────────────────────────

def test_search_no_filter(test_db):
    _insert(test_db, mp_id="mp-10", formula="Al")
    _insert(test_db, mp_id="mp-11", formula="Cu")
    results = test_db.search()
    assert len(results) >= 2


def test_search_by_crystal_system(test_db):
    _insert(test_db, mp_id="mp-20", formula="Fe", crystal_system="cubic")
    _insert(test_db, mp_id="mp-21", formula="Ti", crystal_system="hexagonal")
    results = test_db.search(crystal_system="cubic")
    formulas = [r["formula"] for r in results]
    assert "Fe" in formulas
    assert "Ti" not in formulas


def test_search_by_bandgap_range(test_db):
    _insert(test_db, mp_id="mp-30", formula="Metal", bandgap=0.0)
    _insert(test_db, mp_id="mp-31", formula="Semi", bandgap=1.5)
    _insert(test_db, mp_id="mp-32", formula="Insul", bandgap=5.0)
    results = test_db.search(min_bandgap=0.5, max_bandgap=3.0)
    formulas = [r["formula"] for r in results]
    assert "Semi" in formulas
    assert "Metal" not in formulas
    assert "Insul" not in formulas


def test_search_limit(test_db):
    for i in range(10):
        _insert(test_db, mp_id=f"mp-lim-{i}", formula=f"X{i}")
    results = test_db.search(limit=3)
    assert len(results) == 3


# ── stats ─────────────────────────────────────────────────────────────────────

def test_stats_empty(test_db):
    s = test_db.stats()
    assert s["total"] == 0
    assert s["with_bandgap"] == 0


def test_stats_with_data(test_db):
    _insert(test_db, mp_id="mp-s1", bandgap=1.0)
    _insert(test_db, mp_id="mp-s2", bandgap=None)
    s = test_db.stats()
    assert s["total"] == 2
    assert s["with_bandgap"] == 1


# ── notes ─────────────────────────────────────────────────────────────────────

def test_get_note_missing(test_db):
    assert test_db.get_note("mp-999") == ""


def test_save_and_get_note(test_db):
    test_db.save_note("mp-note1", "Great conductor")
    assert test_db.get_note("mp-note1") == "Great conductor"


def test_save_note_upserts(test_db):
    test_db.save_note("mp-note2", "First")
    test_db.save_note("mp-note2", "Updated")
    assert test_db.get_note("mp-note2") == "Updated"


# ── collection ───────────────────────────────────────────────────────────────

def test_collection_add_and_has(test_db):
    test_db.collection_add("mp-c1", "Fe2O3")
    assert test_db.collection_has("mp-c1") is True
    assert test_db.collection_has("mp-c999") is False


def test_collection_remove(test_db):
    test_db.collection_add("mp-c2", "Al2O3")
    test_db.collection_remove("mp-c2")
    assert test_db.collection_has("mp-c2") is False


def test_collection_get_ordered(test_db):
    test_db.collection_add("mp-c3", "Fe")
    test_db.collection_add("mp-c4", "Si")
    rows = test_db.collection_get()
    mp_ids = [r["mp_id"] for r in rows]
    assert "mp-c3" in mp_ids
    assert "mp-c4" in mp_ids


# ── elasticity / dielectric ───────────────────────────────────────────────────

def test_save_elasticity(test_db):
    _insert(test_db, mp_id="mp-e1", formula="W")
    test_db.save_elasticity("mp-e1", k_voigt=310.0, g_voigt=160.0,
                            young_modulus=400.0, poisson_ratio=0.28,
                            universal_anisotropy=1.2)
    row = test_db.get_material_row("mp-e1")
    assert row["k_voigt"] == pytest.approx(310.0)
    assert row["elastic_fetched"] == 1


def test_save_dielectric(test_db):
    _insert(test_db, mp_id="mp-d1", formula="BaTiO3")
    test_db.save_dielectric("mp-d1", e_total=80.0, e_ionic=60.0,
                            e_electronic=5.0, refractive_index=2.24)
    row = test_db.get_material_row("mp-d1")
    assert row["e_total"] == pytest.approx(80.0)
    assert row["dielectric_fetched"] == 1


# ── ashby / position data ─────────────────────────────────────────────────────

def test_get_ashby_data_invalid_cols(test_db):
    assert test_db.get_ashby_data("malicious; DROP TABLE", "density") == []


def test_get_ashby_data_valid(test_db):
    _insert(test_db, mp_id="mp-a1", density=7.87)
    test_db.save_elasticity("mp-a1", k_voigt=310.0, g_voigt=160.0,
                            young_modulus=400.0, poisson_ratio=0.28,
                            universal_anisotropy=1.2)
    rows = test_db.get_ashby_data("density", "young_modulus")
    assert any(r["mp_id"] == "mp-a1" for r in rows)


# ── pubchem cache ─────────────────────────────────────────────────────────────

def test_save_pubchem(test_db):
    _insert(test_db, mp_id="mp-p1", formula="NaCl")
    test_db.save_pubchem("mp-p1", {"MeltingPoint": "801 °C"})
    import json
    row = test_db.get_material_row("mp-p1")
    assert json.loads(row["pubchem_json"])["MeltingPoint"] == "801 °C"


# ── similarity / ML rows ──────────────────────────────────────────────────────

def test_get_ml_rows_empty(test_db):
    assert test_db.get_ml_rows() == []


def test_get_ml_rows_with_data(test_db):
    _insert(test_db, mp_id="mp-ml1", bandgap=1.1, density=2.33, nsites=2, volume=40.0)
    rows = test_db.get_ml_rows()
    assert len(rows) == 1
    assert "bandgap" in rows[0]
