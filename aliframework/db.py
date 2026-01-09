from __future__ import annotations

"""Relational database connection helpers.

Supports Postgres, MySQL, SQL Server, and Oracle via their Python drivers.

This module intentionally does not hide the underlying drivers; instead it
normalises configuration and returns a low-level connection object.
"""

from typing import Any

from .config import DbConfig, DatabaseType
from .errors import MissingDriverError


def create_db_connection(config: DbConfig) -> Any:
    """Create a DB-API compatible connection object.

    You are responsible for closing the connection when done.
    """

    if config.db_type == DatabaseType.POSTGRES:
        try:
            import psycopg2  # type: ignore
        except ImportError as exc:
            raise MissingDriverError("psycopg2 is required for Postgres") from exc

        return psycopg2.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            dbname=config.database,
            **(config.extra or {}),
        )

    if config.db_type == DatabaseType.MYSQL:
        try:
            import pymysql  # type: ignore
        except ImportError as exc:
            raise MissingDriverError("pymysql is required for MySQL") from exc

        return pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            db=config.database,
            **(config.extra or {}),
        )

    if config.db_type == DatabaseType.MSSQL:
        try:
            import pyodbc  # type: ignore
        except ImportError as exc:
            raise MissingDriverError("pyodbc is required for SQL Server") from exc

        dsn = config.extra.get("dsn") if config.extra else None
        if dsn:
            conn_str = dsn
        else:
            driver = config.extra.get("driver", "ODBC Driver 17 for SQL Server") if config.extra else "ODBC Driver 17 for SQL Server"
            conn_str = (
                f"DRIVER={{{driver}}};SERVER={config.host},{config.port};"
                f"DATABASE={config.database};UID={config.user};PWD={config.password}"
            )
        return pyodbc.connect(conn_str)

    if config.db_type == DatabaseType.ORACLE:
        try:
            import oracledb  # type: ignore
        except ImportError as exc:
            raise MissingDriverError("oracledb (cx_Oracle) is required for Oracle") from exc

        dsn = oracledb.makedsn(config.host, config.port, service_name=config.database)
        return oracledb.connect(
            user=config.user,
            password=config.password,
            dsn=dsn,
            **(config.extra or {}),
        )

    raise ValueError(f"Unsupported db_type: {config.db_type}")

# ---------------------------------------------------------------------------
# Usage examples
# Example: simple CRUD demo (works similarly for Postgres/MySQL)
#
# def demo_crud(conn):
#     cur = conn.cursor()
#     # CREATE
#     cur.execute("CREATE TABLE IF NOT EXISTS items (id INT PRIMARY KEY, name TEXT)")
#     # DELETE existing rows for a clean demo
#     cur.execute("DELETE FROM items")
#     # INSERT
#     cur.execute("INSERT INTO items (id, name) VALUES (%s, %s)", (1, "foo"))
#     # READ
#     cur.execute("SELECT name FROM items WHERE id = %s", (1,))
#     print("read:", cur.fetchone())
#     # UPDATE
#     cur.execute("UPDATE items SET name = %s WHERE id = %s", ("bar", 1))
#     cur.execute("SELECT name FROM items WHERE id = %s", (1,))
#     print("after update:", cur.fetchone())
#     # DELETE
#     cur.execute("DELETE FROM items WHERE id = %s", (1,))
#     conn.commit()
#
# ---------------------------------------------------------------------------
# from aliframework.config import DbConfig, DatabaseType
# from aliframework.db import create_db_connection
#
# # Postgres
# pg_cfg = DbConfig(
#     db_type=DatabaseType.POSTGRES,
#     host="localhost",
#     port=5432,
#     user="pguser",
#     password="pgpass",
#     database="pgdb",
# )
# pg_conn = create_db_connection(pg_cfg)
#
# # MySQL
# mysql_cfg = DbConfig(
#     db_type=DatabaseType.MYSQL,
#     host="localhost",
#     port=3306,
#     user="myuser",
#     password="mypass",
#     database="mydb",
# )
# mysql_conn = create_db_connection(mysql_cfg)
#
# # SQL Server
# mssql_cfg = DbConfig(
#     db_type=DatabaseType.MSSQL,
#     host="localhost",
#     port=1433,
#     user="sa",
#     password="Password123",
#     database="master",
# )
# mssql_conn = create_db_connection(mssql_cfg)
#
# # Oracle (service name in `database`)
# oracle_cfg = DbConfig(
#     db_type=DatabaseType.ORACLE,
#     host="localhost",
#     port=1521,
#     user="system",
#     password="oracle",
#     database="XEPDB1",
# )
# oracle_conn = create_db_connection(oracle_cfg)
