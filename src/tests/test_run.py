import pytest

from sql.run import run, handle_postgres_special


@pytest.fixture
def conn():
    class Connection:
        pass

    connection = Connection()
    connection.name = "conn"
    return connection


@pytest.mark.parametrize("mock_pgspecial", [None])
def test_handle_postgres_special(mock_pgspecial):
    with pytest.raises(ImportError):
        handle_postgres_special("conn", "statement")


@pytest.mark.parametrize(
    "sql, config, user_namespace",
    [
        ("BEGIN", "config", "user_namespace"),
    ],
)
def test_sql_begin_exception(conn, sql, config, user_namespace):
    with pytest.raises(Exception):
        run(conn, sql, config, user_namespace)


@pytest.mark.parametrize(
    "sql, config, user_namespace",
    [
        ("", "config", "user_namespace"),
    ],
)
def test_sql_empty(conn, sql, config, user_namespace):
    assert run(conn, sql, config, user_namespace) == "Connected: %s" % conn.name
