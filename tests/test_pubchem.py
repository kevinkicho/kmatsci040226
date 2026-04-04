"""Tests for pubchem.py — pure formatting helpers only (no network calls)."""
import pubchem


def test_format_prop_present():
    data = {"MeltingPoint": "801", "BoilingPoint": "1413"}
    assert pubchem.format_prop(data, "MeltingPoint", "°C") == "801 °C"


def test_format_prop_no_unit():
    data = {"IUPACName": "sodium chloride"}
    assert pubchem.format_prop(data, "IUPACName") == "sodium chloride"


def test_format_prop_missing_key():
    data = {"MeltingPoint": "801"}
    assert pubchem.format_prop(data, "BoilingPoint") is None


def test_format_prop_empty_string():
    data = {"FlashPoint": ""}
    assert pubchem.format_prop(data, "FlashPoint") is None


def test_format_prop_none_value():
    data = {"MolecularWeight": None}
    assert pubchem.format_prop(data, "MolecularWeight") is None


def test_format_prop_strips_trailing_space():
    data = {"IUPACName": "iron"}
    result = pubchem.format_prop(data, "IUPACName", "")
    assert result == "iron"
    assert not result.endswith(" ")
