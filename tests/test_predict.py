"""Tests for predict.py — ML model building and inference."""
import pytest
import predict


def _make_row(crystal_system="cubic", nsites=4, volume=60.0, density=5.0,
              nelements=2, formation_e=-0.3, bandgap=1.0):
    return {
        "crystal_system": crystal_system,
        "nsites": nsites,
        "volume": volume,
        "density": density,
        "nelements": nelements,
        "formation_energy_per_atom": formation_e,
        "bandgap": bandgap,
    }


CS_ENC = {cs: i for i, cs in enumerate(predict.CRYSTAL_SYSTEMS)}


# ── _row_to_features ──────────────────────────────────────────────────────────

def test_row_to_features_valid():
    row = _make_row()
    feat = predict._row_to_features(row, CS_ENC)
    assert feat is not None
    assert len(feat) == 6
    assert feat[1] == 4.0   # nsites
    assert feat[2] == 60.0  # volume
    assert feat[3] == 5.0   # density


def test_row_to_features_missing_nsites():
    row = _make_row()
    row["nsites"] = None
    assert predict._row_to_features(row, CS_ENC) is None


def test_row_to_features_missing_volume():
    row = _make_row()
    row["volume"] = None
    assert predict._row_to_features(row, CS_ENC) is None


def test_row_to_features_missing_density():
    row = _make_row()
    row["density"] = None
    assert predict._row_to_features(row, CS_ENC) is None


def test_row_to_features_unknown_crystal_system():
    row = _make_row(crystal_system="unknown_system")
    feat = predict._row_to_features(row, CS_ENC)
    assert feat is not None
    assert feat[0] == 0  # falls back to 0 for unknown


def test_row_to_features_none_nelements():
    row = _make_row()
    row["nelements"] = None
    feat = predict._row_to_features(row, CS_ENC)
    assert feat is not None
    assert feat[4] == 1.0  # default


def test_row_to_features_none_formation_e():
    row = _make_row()
    row["formation_energy_per_atom"] = None
    feat = predict._row_to_features(row, CS_ENC)
    assert feat is not None
    assert feat[5] == 0.0  # default


# ── build_model ───────────────────────────────────────────────────────────────

def test_build_model_insufficient_data():
    rows = [_make_row() for _ in range(10)]
    assert predict.build_model(rows) is None


def test_build_model_returns_bundle(model_bundle):
    assert model_bundle is not None
    assert "model" in model_bundle
    assert "cs_enc" in model_bundle
    assert "mae" in model_bundle
    assert model_bundle["n_train"] == 60
    assert model_bundle["mae"] >= 0.0


def test_build_model_feature_importances(model_bundle):
    assert model_bundle is not None
    imps = model_bundle["importances"]
    assert set(imps.keys()) == set(predict.FEATURE_LABELS)
    assert abs(sum(imps.values()) - 1.0) < 1e-6  # importances sum to 1


# ── predict_bandgap ───────────────────────────────────────────────────────────

def test_predict_bandgap_none_bundle():
    assert predict.predict_bandgap(None, _make_row()) is None


def test_predict_bandgap_returns_nonnegative(model_bundle):
    result = predict.predict_bandgap(model_bundle, _make_row(bandgap=None))
    assert result is not None
    assert result >= 0.0


def test_predict_bandgap_incomplete_row(model_bundle):
    incomplete = _make_row()
    incomplete["density"] = None
    assert predict.predict_bandgap(model_bundle, incomplete) is None
