import pytest
import sqlite3
import db as db_module
import predict


# ── Session-scoped DB: one init per test session, not per test ────────────────

@pytest.fixture(scope="session")
def _session_db_path(tmp_path_factory):
    """Create the DB schema once for the whole session."""
    db_path = str(tmp_path_factory.mktemp("session_db") / "test.db")
    original = db_module.DB_PATH
    db_module.DB_PATH = db_path
    db_module.init_db()
    db_module.DB_PATH = original
    return db_path


@pytest.fixture
def test_db(_session_db_path, monkeypatch):
    """Point db module at the shared session DB and roll back after each test."""
    monkeypatch.setattr(db_module, "DB_PATH", _session_db_path)

    # Wrap test in a savepoint so every INSERT/UPDATE rolls back automatically
    conn = sqlite3.connect(_session_db_path)
    conn.execute("SAVEPOINT _test")

    # Intercept get_conn so all db.py calls use this connection (no commit leaks)
    def _get_conn():
        return _SavepointConn(conn)

    monkeypatch.setattr(db_module, "get_conn", _get_conn)
    yield db_module

    # Roll back everything the test wrote
    conn.execute("ROLLBACK TO SAVEPOINT _test")
    conn.execute("RELEASE SAVEPOINT _test")
    conn.close()


class _SavepointConn:
    """Thin wrapper: delegates to the real connection but turns commit() into RELEASE+SAVEPOINT."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._sp_depth = 0

    # Allow `with get_conn() as c:` — the context manager protocol
    def __enter__(self):
        self._sp_depth += 1
        self._conn.execute(f"SAVEPOINT _sp{self._sp_depth}")
        return self

    def __exit__(self, exc, val, tb):
        sp = f"_sp{self._sp_depth}"
        if exc:
            self._conn.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        self._conn.execute(f"RELEASE SAVEPOINT {sp}")
        self._sp_depth -= 1
        return False  # don't suppress exceptions

    def execute(self, sql, params=()):
        return self._conn.execute(sql, params)

    def commit(self):
        pass  # swallowed — isolation is handled by savepoints

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value):
        self._conn.row_factory = value


# ── Session-scoped model: build GradientBoosting once for all predict tests ──

@pytest.fixture(scope="session")
def model_bundle():
    rows = [
        {
            "crystal_system": predict.CRYSTAL_SYSTEMS[i % len(predict.CRYSTAL_SYSTEMS)],
            "nsites": i % 8 + 2,
            "volume": 40.0 + i,
            "density": 2.0 + (i % 10) * 0.5,
            "nelements": 2,
            "formation_energy_per_atom": -0.3,
            "bandgap": float(i % 6),
        }
        for i in range(60)
    ]
    return predict.build_model(rows)
