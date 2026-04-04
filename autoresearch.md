# Autoresearch: Optimize Test Suite Runtime

## Objective
Minimize total pytest wall-clock time for `tests/` (43 tests across test_db.py, test_predict.py, test_pubchem.py).

## Metric
`runtime_s` — extracted from the pytest summary line "N passed in X.XXs"
**Lower is better.**

## Measurement command
```
python -m pytest tests/ -q --tb=no 2>&1 | grep "passed"
```
Parse the float after "in " and before "s".

## Baseline
~8.5s (average of 3 runs: 8.65, 8.38, 8.56).
Breakdown: test_db.py ~7s, test_predict.py ~1.25s, test_pubchem.py ~0.08s.

## Root cause (profiled)
- test_db.py setup is ~0.28–0.32s per test × 24 tests ≈ 7s
  - Each test calls `init_db()` + `migrate_db()` on a fresh tmp_path DB
  - `migrate_db()` runs 24 ALTER TABLE statements on a newly-created schema (all columns missing → all added)
  - First import of pymatgen (from db.py) adds ~1–2s one-time cost
- test_predict.py: 3 tests call `build_model()` with GradientBoosting(n_estimators=200) → slow

## Files that can be changed
- `tests/conftest.py` — fixture scope, shared state
- `tests/test_db.py` — test structure
- `tests/test_predict.py` — model fixture sharing

## Constraints
- All 43 tests must remain passing
- No changes to source modules (db.py, predict.py, pubchem.py)
- Tests must remain correct (no stubbing out real behavior)

## Ideas to try (ordered by expected impact)
1. **Session-scoped DB fixture** — create one DB once for the whole session; use unique mp_ids per test to avoid collisions. Expected savings: ~6s (eliminates 24× init_db overhead)
2. **Session-scoped model fixture** — build the GradientBoosting model once and reuse across all 3 predict tests that need it. Expected savings: ~0.8s
3. **pytest-xdist parallel** — run tests in parallel with `pytest -n auto`. Requires session-scoped fixtures to be thread-safe (or per-worker).
4. **Skip migrate_db in fresh DB** — since test DBs are always empty, we could pre-create the full schema with all columns, avoiding ALTER TABLE calls. But this requires changing db.py (not allowed).
5. **Use in-memory SQLite** — patch get_conn to return a shared in-memory connection. Avoids filesystem I/O. Requires careful connection sharing.

## Experiment log

| Run | Label | Runtime | Δ vs baseline | Kept |
|-----|-------|---------|---------------|------|
| 0 | baseline | 8.53s | — | ✓ |
| 1 | session_db_savepoint_shared_model | **0.75s** | −91% | ✓ BEST |
| 2 | xdist parallel | 6.09s | −29% | ✗ |

## Best result: Run 1 — 0.75s (11× speedup)

**What changed in `tests/conftest.py`:**
- `_session_db_path` (session-scoped): calls `init_db()` once per session instead of 24×
- `test_db` fixture: uses `_SavepointConn` wrapper — wraps each test in a SQLite SAVEPOINT + ROLLBACK for isolation without re-creating the DB
- `model_bundle` (session-scoped): builds `GradientBoostingRegressor` once for all predict tests instead of 3×

**What changed in `tests/test_predict.py`:**
- `test_build_model_returns_bundle`, `test_build_model_feature_importances`, `test_predict_bandgap_returns_nonnegative`, `test_predict_bandgap_incomplete_row` — all use the shared `model_bundle` fixture

**Remaining time (irreducible):**
- ~0.29s one-time: pymatgen import + `init_db()` + first GBR model build
- ~0.46s: running 43 test bodies + savepoint overhead

## Further ideas (diminishing returns)
- Lazy-import pymatgen in db.py (would save ~0.15s) — requires changing source module (not allowed)
- Cache pymatgen import with importlib tricks — fragile
- Reduce GBR n_estimators in test data — would change model behavior
- At 0.75s for 43 tests, further optimization offers minimal practical benefit
