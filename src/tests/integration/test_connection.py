import pytest
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
import duckdb_engine


from sql.connection import Connection, DBAPIConnection


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
            "duckdb",
            "duckdb",
            "duckdb",
        ],
        [
            "setup_duckDB",
            Connection,
            None,
            "@/tmp/db-duckdb",
            duckdb_engine.Dialect,
            "duckdb:////tmp/db-duckdb",
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
