import types
import sys

import pytest

from aliframework.config import DbConfig, DatabaseType
from aliframework import db


def test_create_postgres_connection_uses_psycopg2(monkeypatch):
    calls = {}

    class DummyPsycopg2Module(types.SimpleNamespace):
        def connect(self, **kwargs):  # type: ignore[override]
            calls["kwargs"] = kwargs
            return "PG-CONN"

    monkeypatch.setitem(sys.modules, "psycopg2", DummyPsycopg2Module())

    cfg = DbConfig(
        db_type=DatabaseType.POSTGRES,
        host="localhost",
        port=5432,
        user="u",
        password="p",
        database="d",
    )
    conn = db.create_db_connection(cfg)
    assert conn == "PG-CONN"
    assert calls["kwargs"]["host"] == "localhost"
