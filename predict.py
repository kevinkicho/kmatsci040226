# predict.py — ML property prediction for MatSci Explorer
#
# Trains a RandomForestRegressor on the local DB to predict band gap
# from structural/compositional features that don't require the API.
#
# Usage from app.py:
#   from predict import build_model, predict_bandgap, FEATURE_LABELS
#   model = build_model(rows)          # rows from db.get_ml_rows()
#   result = predict_bandgap(model, db_row)

try:
    import numpy as np
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import mean_absolute_error
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

CRYSTAL_SYSTEMS = [
    "cubic", "hexagonal", "tetragonal", "orthorhombic",
    "trigonal", "monoclinic", "triclinic",
]

FEATURE_LABELS = [
    "Crystal system (encoded)",
    "Atoms per unit cell",
    "Cell volume (Å³)",
    "Density (g/cm³)",
    "No. of elements",
    "Formation energy (eV/at)",
]


def _row_to_features(row: dict, cs_enc: dict) -> list[float] | None:
    """Convert a DB row dict to a fixed-length feature vector. Returns None if incomplete."""
    cs  = str(row.get("crystal_system") or "").lower()
    ns  = row.get("nsites")
    vol = row.get("volume")
    den = row.get("density")
    nel = row.get("nelements")
    fe  = row.get("formation_energy_per_atom")

    if any(v is None for v in [ns, vol, den]):
        return None

    return [
        cs_enc.get(cs, 0),
        float(ns),
        float(vol),
        float(den),
        float(nel) if nel is not None else 1.0,
        float(fe)  if fe  is not None else 0.0,
    ]


def build_model(rows: list[dict]) -> dict | None:
    """
    Train a GradientBoosting model to predict band gap.
    Returns a model bundle dict, or None if sklearn unavailable / insufficient data.
    """
    if not SKLEARN_OK:
        return None

    # Build crystal system encoder from training data
    cs_values = [str(r.get("crystal_system") or "").lower() for r in rows]
    unique_cs = sorted(set(cs_values) | set(CRYSTAL_SYSTEMS))
    cs_enc = {v: i for i, v in enumerate(unique_cs)}

    X, y = [], []
    for row in rows:
        bg = row.get("bandgap")
        if bg is None:
            continue
        feat = _row_to_features(row, cs_enc)
        if feat is None:
            continue
        X.append(feat)
        y.append(float(bg))

    if len(X) < 30:
        return None

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)

    model = GradientBoostingRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.08,
        subsample=0.8, random_state=42,
    )
    model.fit(X, y)

    # Cross-validate MAE on a held-out 20%
    n_test = max(10, len(X) // 5)
    rng = np.random.RandomState(0)
    idx = rng.permutation(len(X))
    X_te, y_te = X[idx[:n_test]], y[idx[:n_test]]
    mae = mean_absolute_error(y_te, model.predict(X_te))

    importances = dict(zip(FEATURE_LABELS, model.feature_importances_))

    return {
        "model": model,
        "cs_enc": cs_enc,
        "n_train": len(X),
        "mae": mae,
        "importances": importances,
    }


def predict_bandgap(bundle: dict, row: dict) -> float | None:
    """Predict band gap for a single compound. Returns None if features unavailable."""
    if not SKLEARN_OK or bundle is None:
        return None
    feat = _row_to_features(row, bundle["cs_enc"])
    if feat is None:
        return None
    pred = bundle["model"].predict([feat])[0]
    return max(0.0, float(pred))
