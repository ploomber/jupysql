from unittest.mock import ANY
from functools import partial


import pytest


from sql.connection import Connection, DBAPIConnection, ConnectionManager


@pytest.mark.parametrize(
    "dynamic_db, Constructor, alias, dialect",
    [
        [
            "setup_postgreSQL",
            Connection,
            "postgresql://ploomber_app:***@localhost:5432/db",
            "postgresql",
        ],
        [
            "setup_duckDB_native",
            DBAPIConnection,
            "DuckDBPyConnection",
            "duckdb",
        ],
        [
            "setup_duckDB",
            Connection,
            "duckdb:////tmp/db-duckdb",
            "duckdb",
        ],
        [
            "setup_postgreSQL",
            partial(Connection, alias="some-postgres"),
            "some-postgres",
            "postgresql",
        ],
        [
            "setup_duckDB_native",
            partial(DBAPIConnection, alias="some-duckdb"),
            "some-duckdb",
            "duckdb",
        ],
    ],
)
def test_connection_properties(dynamic_db, request, Constructor, alias, dialect):
    dynamic_db = request.getfixturevalue(dynamic_db)

    conn = Constructor(dynamic_db)

    assert conn.alias == alias
    assert conn.dialect == dialect


@pytest.mark.parametrize(
    "dynamic_db, Constructor, expected",
    [
        [
            "setup_postgreSQL",
            Connection,
            "postgresql://ploomber_app:***@localhost:5432/db",
        ],
        [
            "setup_duckDB",
            Connection,
            "duckdb:////tmp/db-duckdb",
        ],
        [
            "setup_duckDB_native",
            DBAPIConnection,
            "DuckDBPyConnection",
        ],
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


@pytest.mark.parametrize(
    "dynamic_db, Constructor, expected",
    [
        [
            "setup_postgreSQL",
            Connection,
            {
                "dialect": "postgresql",
                "driver": "psycopg2",
                "server_version_info": ANY,
            },
        ],
        [
            "setup_duckDB",
            Connection,
            {
                "dialect": "duckdb",
                "driver": "duckdb_engine",
                "server_version_info": ANY,
            },
        ],
        [
            "setup_duckDB_native",
            DBAPIConnection,
            {
                "dialect": "duckdb",
                "driver": "DuckDBPyConnection",
                "server_version_info": ANY,
            },
        ],
    ],
    ids=[
        "postgresql",
        "duckdb",
        "duckdb_native",
    ],
)
def test_get_database_information(dynamic_db, request, Constructor, expected):
    conn = Constructor(request.getfixturevalue(dynamic_db))
    assert conn._get_database_information() == expected