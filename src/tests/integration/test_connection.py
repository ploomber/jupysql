from functools import partial


import pytest
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
import duckdb_engine


from sql.connection import Connection, DBAPIConnection, ConnectionManager


@pytest.mark.parametrize(
    "dynamic_db, Constructor, alias, name, dialect, url",
    [
        [
            "setup_postgreSQL",
            Connection,
            None,
            "ploomber_app@db",
            PGDialect_psycopg2,
            "postgresql://ploomber_app:***@localhost:5432/db",
        ],
        [
            "setup_duckDB_native",
            DBAPIConnection,
            None,
            "DuckDBPyConnection",
            "duckdb",
            "DuckDBPyConnection",
        ],
        [
            "setup_duckDB",
            Connection,
            None,
            "@/tmp/db-duckdb",
            duckdb_engine.Dialect,
            "duckdb:////tmp/db-duckdb",
        ],
        [
            "setup_postgreSQL",
            partial(Connection, alias="some-postgres"),
            "some-postgres",
            "ploomber_app@db",
            PGDialect_psycopg2,
            "postgresql://ploomber_app:***@localhost:5432/db",
        ],
        [
            "setup_duckDB_native",
            partial(DBAPIConnection, alias="some-duckdb"),
            "some-duckdb",
            "DuckDBPyConnection",
            "duckdb",
            "DuckDBPyConnection",
        ],
    ],
)
def test_connection_properties(
    dynamic_db, request, Constructor, alias, name, dialect, url
):
    dynamic_db = request.getfixturevalue(dynamic_db)

    conn = Constructor(dynamic_db)

    assert conn.alias == alias
    assert conn.name == name
    assert conn.dialect == dialect
    assert conn.url == url


@pytest.mark.parametrize(
    "dynamic_db, Constructor, expected",
    [
        [
            "setup_postgreSQL",
            Connection,
            "postgresql://ploomber_app:***@localhost:5432/db",
        ],
        ["setup_duckDB", Connection, "duckdb:////tmp/db-duckdb"],
        ["setup_duckDB_native", DBAPIConnection, "DuckDBPyConnection"],
        [
            "setup_duckDB",
            partial(Connection, alias="some-alias"),
            "some-alias",
        ],
        [
            "setup_duckDB_native",
            partial(DBAPIConnection, alias="another-alias"),
            "another-alias",
        ],
    ],
)
def test_connection_identifiers(
    dynamic_db, request, monkeypatch, Constructor, expected
):
    connections = {}
    monkeypatch.setattr(ConnectionManager, "connections", connections)

    dynamic_db = request.getfixturevalue(dynamic_db)

    Constructor(dynamic_db)

    assert len(connections) == 1
    assert set(connections) == {expected}
