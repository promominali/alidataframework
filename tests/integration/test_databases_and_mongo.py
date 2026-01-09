from __future__ import annotations

"""Integration tests for Postgres, MySQL, and MongoDB.

Requires docker-compose services to be running:
  postgres: localhost:5432 (pguser/pgpass, pgdb)
  mysql:    localhost:3306 (myuser/mypass, mydb)
  mongo:    localhost:27017
"""

import pytest

from aliframework.config import DbConfig, DatabaseType
from aliframework.db import create_db_connection
from aliframework.nosql import create_mongo_client
from .conftest import wait_for_port


@pytest.mark.integration
def test_postgres_connection_and_query():
    pytest.importorskip("psycopg2")
    wait_for_port("localhost", 5432, timeout=60)

    cfg = DbConfig(
        db_type=DatabaseType.POSTGRES,
        host="localhost",
        port=5432,
        user="pguser",
        password="pgpass",
        database="pgdb",
    )
    conn = create_db_connection(cfg)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS test_table (id INT PRIMARY KEY, value TEXT)")
    cur.execute("DELETE FROM test_table")
    cur.execute("INSERT INTO test_table (id, value) VALUES (%s, %s)", (1, "hello"))
    cur.execute("SELECT value FROM test_table WHERE id = %s", (1,))
    row = cur.fetchone()
    conn.commit()
    conn.close()

    assert row[0] == "hello"


@pytest.mark.integration
def test_mysql_connection_and_query():
    pytest.importorskip("pymysql")
    wait_for_port("localhost", 3306, timeout=60)

    cfg = DbConfig(
        db_type=DatabaseType.MYSQL,
        host="localhost",
        port=3306,
        user="myuser",
        password="mypass",
        database="mydb",
    )
    conn = create_db_connection(cfg)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS test_table (id INT PRIMARY KEY, value VARCHAR(255))")
    cur.execute("DELETE FROM test_table")
    cur.execute("INSERT INTO test_table (id, value) VALUES (%s, %s)", (1, "hello"))
    cur.execute("SELECT value FROM test_table WHERE id = %s", (1,))
    row = cur.fetchone()
    conn.commit()
    conn.close()

    assert row[0] == "hello"


@pytest.mark.integration
def test_mongo_connection_and_ping():
    pytest.importorskip("pymongo")
    wait_for_port("localhost", 27017, timeout=60)

    client = create_mongo_client("mongodb://localhost:27017")
    result = client.admin.command("ping")
    assert result["ok"] == 1.0
