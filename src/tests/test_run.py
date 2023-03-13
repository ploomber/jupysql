import pytest
import sqlparse

from sql.run import run


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
        assert mock_pgspecial is None


@pytest.mark.parametrize(
    "conn, sql, config, user_namespace", ["conn", "BEGIN", "config", "user_namespace"]
)
def test_sql_begin_exception(conn, sql, config, user_namespace):
    with pytest.raises(Exception):
        for _ in sqlparse.split(sql):
            first_word = sql.strip().split()[0].lower()
        assert first_word == "begin"


@pytest.mark.parametrize(
    "sql, config, user_namespace", ["", "config", "user_namespace"]
)
def test_sql_empty(conn, sql, config, user_namespace):
    assert run(conn, sql, config, user_namespace) == "Connected: %s" % conn.name
