import math
import pytest
from IPython.core.error import UsageError
from pathlib import Path

from sqlalchemy import create_engine
from sql.connection import SQLAlchemyConnection
from sql.inspect import _is_numeric
from sql.display import Table, Message
from sql.widgets import TableWidget
from jupysql_plugin.widgets import ConnectorWidget
import duckdb
import sqlite3


VALID_COMMANDS_MESSAGE = (
    "Valid commands are: tables, columns, test, profile, explore, snippets, connect"
)


def _get_row_string(row, column_name):
    """
    Helper function to retrieve the string value of a specific column in a table row.

    Parameters
     ----------
        row: PrettyTable row object.
        column_name: Name of the column.

    Returns:
        String value of the specified column in the row.
    """
    return row.get_string(fields=[column_name], border=False, header=False).strip()


@pytest.fixture
def ip_snippets(ip):
    ip.run_cell("%sql sqlite://")
    ip.run_cell(
        """
%%sql --save high_price --no-execute
SELECT *
FROM "test_store"
WHERE price >= 1.50
"""
    )
    ip.run_cell(
        """
%%sql --save high_price_a --no-execute
SELECT *
FROM "high_price"
WHERE symbol == 'a'
"""
    )
    ip.run_cell(
        """
%%sql --save high_price_b --no-execute
SELECT *
FROM "high_price"
WHERE symbol == 'b'
"""
    )
    yield ip


@pytest.fixture
def ip_with_connections(ip_empty):
    ip_empty.run_cell("%sql duckdb:// --alias duckdb_sqlalchemy")
    ip_empty.run_cell("%sql sqlite:// --alias sqlite_sqlalchemy")
    duckdb_dbapi = duckdb.connect("")
    sqlite_dbapi = sqlite3.connect("")

    ip_empty.push({"duckdb_dbapi": duckdb_dbapi})
    ip_empty.push({"sqlite_dbapi": sqlite_dbapi})

    yield ip_empty


@pytest.fixture
def test_snippet_ip(ip):
    ip.run_cell("%sql sqlite://")
    yield ip


@pytest.fixture
def sample_schema_with_table(ip_empty):
    ip_empty.run_cell("%sql duckdb://")
    ip_empty.run_cell(
        """%%sql
CREATE SCHEMA schema1;
CREATE TABLE schema1.table1 (x INT, y TEXT);
INSERT INTO schema1.table1 VALUES (1, 'one');
INSERT INTO schema1.table1 VALUES (2, 'two');
"""
    )


@pytest.mark.parametrize(
    "cmd, cols, table_name",
    [
        [
            "%sqlcmd columns -t {{table}}",
            ["first_name", "last_name", "year_of_death"],
            "author",
        ],
        ["%sqlcmd columns -t {{table}}", ["first", "second"], "table with spaces"],
        ["%sqlcmd columns -t {{table}}", ["first", "second"], "table with spaces"],
    ],
)
def test_columns_with_variable_substitution(ip, cmd, cols, table_name):
    ip.user_global_ns["table"] = table_name
    out = ip.run_cell(cmd).result._repr_html_()
    assert all(col in out for col in cols)


@pytest.mark.parametrize(
    "cell, error_message",
    [
        [
            "%sqlcmd",
            "Missing argument for %sqlcmd. " f"{VALID_COMMANDS_MESSAGE}",
        ],
        [
            "%sqlcmd ",
            "Missing argument for %sqlcmd. " f"{VALID_COMMANDS_MESSAGE}",
        ],
        [
            "%sqlcmd  ",
            "Missing argument for %sqlcmd. " f"{VALID_COMMANDS_MESSAGE}",
        ],
        [
            "%sqlcmd   ",
            "Missing argument for %sqlcmd. " f"{VALID_COMMANDS_MESSAGE}",
        ],
        [
            "%sqlcmd stuff",
            "%sqlcmd has no command: 'stuff'. " f"{VALID_COMMANDS_MESSAGE}",
        ],
        [
            "%sqlcmd columns",
            "the following arguments are required: -t/--table",
        ],
    ],
)
def test_error(tmp_empty, ip, cell, error_message):
    with pytest.raises(UsageError) as excinfo:
        ip.run_cell(cell)

    assert excinfo.value.error_type == "UsageError"
    assert str(excinfo.value) == error_message


@pytest.mark.parametrize(
    "command",
    [
        "tables",
        "columns",
        "test",
        "profile",
        "explore",
    ],
)
def test_sqlcmd_error_when_no_connection(ip_empty, command):
    with pytest.raises(UsageError) as excinfo:
        ip_empty.run_cell(f"%sqlcmd {command}")

    assert excinfo.value.error_type == "RuntimeError"
    assert str(excinfo.value) == (
        f"Cannot execute %sqlcmd {command} because there is no "
        "active connection. Connect to a database and try again."
    )


def test_sqlcmd_snippets_when_no_connection(ip_empty, capsys):
    ip_empty.run_cell("%sqlcmd snippets")
    captured = capsys.readouterr()
    assert "No snippets stored" in captured.out


@pytest.mark.parametrize(
    "query, command",
    [
        ("%sqlcmd tables", "tables"),
        ("%sqlcmd columns --table penguins.csv", "columns"),
        (
            "%sqlcmd test --table penguins.csv  --column body_mass_g --greater 2900",
            "test",
        ),
        ("%sqlcmd explore --table penguins.csv", "explore"),
    ],
)
def test_sqlcmd_not_supported_error(ip_with_connections, query, command, capsys):
    ip_with_connections.run_cell("%sql duckdb_dbapi")
    expected_error_message = (
        f"%sqlcmd {command} is only supported with SQLAlchemy connections, "
        "not with DBAPI connections"
    )
    with pytest.raises(UsageError) as excinfo:
        ip_with_connections.run_cell(query)

    assert expected_error_message in str(excinfo.value)


def test_tables(ip):
    out = ip.run_cell("%sqlcmd tables").result._repr_html_()
    assert "author" in out
    assert "empty_table" in out
    assert "test" in out


def test_tables_with_schema(ip, tmp_empty):
    conn = SQLAlchemyConnection(engine=create_engine("sqlite:///my.db"))
    conn.execute("CREATE TABLE numbers (some_number FLOAT)")

    ip.run_cell(
        """%%sql
ATTACH DATABASE 'my.db' AS some_schema
"""
    )

    out = ip.run_cell("%sqlcmd tables --schema some_schema").result._repr_html_()

    assert "numbers" in out


def test_tables_with_schema_variable_substitution(ip, tmp_empty):
    conn = SQLAlchemyConnection(engine=create_engine("sqlite:///my.db"))
    conn.execute("CREATE TABLE numbers (some_number FLOAT)")

    ip.user_global_ns["schema"] = "some_schema"

    ip.run_cell(
        """%%sql
ATTACH DATABASE 'my.db' AS {{schema}}
"""
    )

    out = ip.run_cell("%sqlcmd tables --schema {{schema}}").result._repr_html_()

    assert "numbers" in out


@pytest.mark.parametrize(
    "cmd, cols",
    [
        ["%sqlcmd columns -t author", ["first_name", "last_name", "year_of_death"]],
        [
            "%sqlcmd columns -t 'table with spaces'",
            ["first", "second"],
        ],
        [
            '%sqlcmd columns -t "table with spaces"',
            ["first", "second"],
        ],
    ],
)
def test_columns(ip, cmd, cols):
    out = ip.run_cell(cmd).result._repr_html_()
    assert all(col in out for col in cols)


@pytest.mark.parametrize(
    "arguments", ["--table numbers --schema some_schema", "--table some_schema.numbers"]
)
def test_columns_with_schema(ip, tmp_empty, arguments):
    conn = SQLAlchemyConnection(engine=create_engine("sqlite:///my.db"))
    conn.execute("CREATE TABLE numbers (some_number FLOAT)")

    ip.run_cell(
        """%%sql
ATTACH DATABASE 'my.db' AS some_schema
"""
    )

    out = ip.run_cell(f"%sqlcmd columns {arguments}").result._repr_html_()

    assert "some_number" in out


@pytest.mark.parametrize(
    "arguments",
    ["--table {{table}} --schema {{schema}}", "--table {{schema}}.{{table}}"],
)
def test_columns_with_schema_variable_substitution(ip, tmp_empty, arguments):
    conn = SQLAlchemyConnection(engine=create_engine("sqlite:///my.db"))
    conn.execute("CREATE TABLE numbers (some_number FLOAT)")

    ip.user_global_ns["table"] = "numbers"
    ip.user_global_ns["schema"] = "some_schema"

    ip.run_cell(
        """%%sql
ATTACH DATABASE 'my.db' AS {{schema}}
"""
    )

    out = ip.run_cell(f"%sqlcmd columns {arguments}").result._repr_html_()

    assert "some_number" in out


@pytest.mark.parametrize(
    "conn",
    [
        ("sqlite_sqlalchemy"),
        ("sqlite_dbapi"),
    ],
)
def test_table_profile(ip_with_connections, tmp_empty, conn):
    ip_with_connections.run_cell(f"%sql {conn}")
    ip_with_connections.run_cell(
        """
    %%sql
    CREATE TABLE numbers (rating float, price float, number int, word varchar(50));
    INSERT INTO numbers VALUES (14.44, 2.48, 82, 'a');
    INSERT INTO numbers VALUES (13.13, 1.50, 93, 'b');
    INSERT INTO numbers VALUES (12.59, 0.20, 98, 'a');
    INSERT INTO numbers VALUES (11.54, 0.41, 89, 'a');
    INSERT INTO numbers VALUES (10.532, 0.1, 88, 'c');
    INSERT INTO numbers VALUES (11.5, 0.2, 84, '   ');
    INSERT INTO numbers VALUES (11.1, 0.3, 90, 'a');
    INSERT INTO numbers VALUES (12.9, 0.31, 86, '');
    """
    )

    expected = {
        "count": [8, 8, 8, 8],
        "mean": ["12.2165", "0.6875", "88.7500", math.nan],
        "min": [10.532, 0.1, 82, math.nan],
        "max": [14.44, 2.48, 98, math.nan],
        "unique": [8, 7, 8, 5],
        "freq": [math.nan, math.nan, math.nan, 4],
        "top": [math.nan, math.nan, math.nan, "a"],
    }

    out = ip_with_connections.run_cell("%sqlcmd profile -t numbers").result

    stats_table = out._table

    assert len(stats_table.rows) == len(expected)

    for row in stats_table:
        profile_metric = _get_row_string(row, " ")
        rating = _get_row_string(row, "rating")
        price = _get_row_string(row, "price")
        number = _get_row_string(row, "number")
        word = _get_row_string(row, "word")

        assert profile_metric in expected
        assert rating == str(expected[profile_metric][0])
        assert price == str(expected[profile_metric][1])
        assert number == str(expected[profile_metric][2])
        assert word == str(expected[profile_metric][3])

    # Test sticky column style was injected
    assert "position: sticky;" in out._table_html


@pytest.mark.parametrize(
    "conn",
    [
        ("sqlite_sqlalchemy"),
        ("sqlite_dbapi"),
    ],
)
def test_table_profile_with_substitution(ip_with_connections, tmp_empty, conn):
    ip_with_connections.run_cell(f"%sql {conn}")
    ip_with_connections.run_cell(
        """
    %%sql
    CREATE TABLE numbers (rating float, price float, number int, word varchar(50));
    INSERT INTO numbers VALUES (14.44, 2.48, 82, 'a');
    INSERT INTO numbers VALUES (13.13, 1.50, 93, 'b');
    INSERT INTO numbers VALUES (12.59, 0.20, 98, 'a');
    INSERT INTO numbers VALUES (11.54, 0.41, 89, 'a');
    INSERT INTO numbers VALUES (10.532, 0.1, 88, 'c');
    INSERT INTO numbers VALUES (11.5, 0.2, 84, '   ');
    INSERT INTO numbers VALUES (11.1, 0.3, 90, 'a');
    INSERT INTO numbers VALUES (12.9, 0.31, 86, '');
    """
    )

    expected = {
        "count": [8, 8, 8, 8],
        "mean": ["12.2165", "0.6875", "88.7500", math.nan],
        "min": [10.532, 0.1, 82, math.nan],
        "max": [14.44, 2.48, 98, math.nan],
        "unique": [8, 7, 8, 5],
        "freq": [math.nan, math.nan, math.nan, 4],
        "top": [math.nan, math.nan, math.nan, "a"],
    }

    ip_with_connections.user_global_ns["table"] = "numbers"

    out = ip_with_connections.run_cell("%sqlcmd profile -t {{table}}").result

    stats_table = out._table

    assert len(stats_table.rows) == len(expected)

    for row in stats_table:
        profile_metric = _get_row_string(row, " ")
        rating = _get_row_string(row, "rating")
        price = _get_row_string(row, "price")
        number = _get_row_string(row, "number")
        word = _get_row_string(row, "word")

        assert profile_metric in expected
        assert rating == str(expected[profile_metric][0])
        assert price == str(expected[profile_metric][1])
        assert number == str(expected[profile_metric][2])
        assert word == str(expected[profile_metric][3])

    # Test sticky column style was injected
    assert "position: sticky;" in out._table_html


@pytest.mark.parametrize(
    "conn",
    [
        ("duckdb_sqlalchemy"),
        ("duckdb_dbapi"),
    ],
)
def test_table_profile_with_stdev(ip_with_connections, tmp_empty, conn):
    ip_with_connections.run_cell(f"%sql {conn}")
    ip_with_connections.run_cell(
        """
    %%sql
    CREATE TABLE numbers (rating float, price float, number int, word varchar(50));
    INSERT INTO numbers VALUES (14.44, 2.48, 82, 'a');
    INSERT INTO numbers VALUES (13.13, 1.50, 93, 'b');
    INSERT INTO numbers VALUES (12.59, 0.20, 98, 'a');
    INSERT INTO numbers VALUES (11.54, 0.41, 89, 'a');
    INSERT INTO numbers VALUES (10.532, 0.1, 88, 'c');
    INSERT INTO numbers VALUES (11.5, 0.2, 84, '   ');
    INSERT INTO numbers VALUES (11.1, 0.3, 90, 'a');
    INSERT INTO numbers VALUES (12.9, 0.31, 86, '');
    """
    )

    expected = {
        "count": [8, 8, 8, 8],
        "mean": ["12.2165", "0.6875", "88.7500", math.nan],
        "min": [10.532, 0.1, 82, math.nan],
        "max": [14.44, 2.48, 98, math.nan],
        "unique": [8, 7, 8, 5],
        "freq": [math.nan, math.nan, math.nan, 4],
        "top": [math.nan, math.nan, math.nan, "a"],
        "std": ["1.1958", "0.7956", "4.7631", math.nan],
        "25%": ["11.1000", "0.2000", "84.0000", math.nan],
        "50%": ["11.5400", "0.3000", "88.0000", math.nan],
        "75%": ["12.9000", "0.4100", "90.0000", math.nan],
    }

    out = ip_with_connections.run_cell("%sqlcmd profile -t numbers").result

    stats_table = out._table

    assert len(stats_table.rows) == len(expected)

    for row in stats_table:
        profile_metric = _get_row_string(row, " ")
        rating = _get_row_string(row, "rating")
        price = _get_row_string(row, "price")
        number = _get_row_string(row, "number")
        word = _get_row_string(row, "word")

        assert profile_metric in expected
        assert rating == str(expected[profile_metric][0])
        assert price == str(expected[profile_metric][1])
        assert number == str(expected[profile_metric][2])
        assert word == str(expected[profile_metric][3])

    # Test sticky column style was injected
    assert "position: sticky;" in out._table_html


@pytest.mark.parametrize(
    "arguments", ["--table t --schema b_schema", "--table b_schema.t"]
)
def test_table_schema_profile(ip, tmp_empty, arguments):
    ip.run_cell("%sql sqlite:///a.db")
    ip.run_cell("%sql CREATE TABLE t (n FLOAT)")
    ip.run_cell("%sql INSERT INTO t VALUES (1)")
    ip.run_cell("%sql INSERT INTO t VALUES (2)")
    ip.run_cell("%sql INSERT INTO t VALUES (3)")
    ip.run_cell("%sql --close sqlite:///a.db")

    ip.run_cell("%sql sqlite:///b.db")
    ip.run_cell("%sql CREATE TABLE t (n FLOAT)")
    ip.run_cell("%sql INSERT INTO t VALUES (11)")
    ip.run_cell("%sql INSERT INTO t VALUES (22)")
    ip.run_cell("%sql INSERT INTO t VALUES (33)")
    ip.run_cell("%sql --close sqlite:///b.db")

    ip.run_cell(
        """
    %%sql sqlite://
    ATTACH DATABASE 'a.db' AS a_schema;
    ATTACH DATABASE 'b.db' AS b_schema;
    """
    )

    expected = {
        "count": ["3"],
        "mean": ["22.0000"],
        "min": ["11.0"],
        "max": ["33.0"],
        "std": ["11.0000"],
        "unique": ["3"],
        "freq": [math.nan],
        "top": [math.nan],
    }

    out = ip.run_cell(f"%sqlcmd profile {arguments}").result

    stats_table = out._table

    for row in stats_table:
        profile_metric = _get_row_string(row, " ")

        cell = row.get_string(fields=["n"], border=False, header=False).strip()

        if profile_metric in expected:
            assert cell == str(expected[profile_metric][0])


@pytest.mark.parametrize(
    "arguments",
    ["--table {{table}} --schema {{schema}}", "--table {{schema}}.{{table}}"],
)
def test_table_schema_profile_with_substitution(ip, tmp_empty, arguments):
    ip.run_cell("%sql sqlite:///a.db")
    ip.run_cell("%sql CREATE TABLE t (n FLOAT)")
    ip.run_cell("%sql INSERT INTO t VALUES (1)")
    ip.run_cell("%sql INSERT INTO t VALUES (2)")
    ip.run_cell("%sql INSERT INTO t VALUES (3)")
    ip.run_cell("%sql --close sqlite:///a.db")

    ip.run_cell("%sql sqlite:///b.db")
    ip.run_cell("%sql CREATE TABLE t (n FLOAT)")
    ip.run_cell("%sql INSERT INTO t VALUES (11)")
    ip.run_cell("%sql INSERT INTO t VALUES (22)")
    ip.run_cell("%sql INSERT INTO t VALUES (33)")
    ip.run_cell("%sql --close sqlite:///b.db")

    ip.run_cell(
        """
    %%sql sqlite://
    ATTACH DATABASE 'a.db' AS a_schema;
    ATTACH DATABASE 'b.db' AS b_schema;
    """
    )

    expected = {
        "count": ["3"],
        "mean": ["22.0000"],
        "min": ["11.0"],
        "max": ["33.0"],
        "std": ["11.0000"],
        "unique": ["3"],
        "freq": [math.nan],
        "top": [math.nan],
    }

    ip.user_global_ns["table"] = "t"
    ip.user_global_ns["schema"] = "b_schema"
    out = ip.run_cell(f"%sqlcmd profile {arguments}").result

    stats_table = out._table

    for row in stats_table:
        profile_metric = _get_row_string(row, " ")

        cell = row.get_string(fields=["n"], border=False, header=False).strip()

        if profile_metric in expected:
            assert cell == str(expected[profile_metric][0])


@pytest.mark.parametrize(
    "arguments",
    ["--table sample_table --schema test_schema", "--table test_schema.sample_table"],
)
def test_sqlcmd_profile_with_schema_argument_and_dbapi(ip_empty, tmp_empty, arguments):
    sqlite_dbapi_testdb_conn = sqlite3.connect("test.db")
    ip_empty.push({"sqlite_dbapi_testdb_conn": sqlite_dbapi_testdb_conn})

    ip_empty.run_cell(
        """%%sql sqlite_dbapi_testdb_conn
CREATE TABLE sample_table (n FLOAT);
INSERT INTO sample_table VALUES (11);
INSERT INTO sample_table VALUES (22);
INSERT INTO sample_table VALUES (33);
"""
    )

    ip_empty.run_cell(
        """
    %%sql sqlite_dbapi_testdb_conn
    ATTACH DATABASE 'test.db' AS test_schema;
    """
    )

    expected = {
        "count": ["3"],
        "mean": ["22.0000"],
        "min": ["11.0"],
        "max": ["33.0"],
        "std": ["11.0000"],
        "unique": ["3"],
        "freq": [math.nan],
        "top": [math.nan],
    }

    out = ip_empty.run_cell(f"%sqlcmd profile {arguments}").result

    stats_table = out._table

    for row in stats_table:
        profile_metric = _get_row_string(row, " ")

        cell = row.get_string(fields=["n"], border=False, header=False).strip()

        if profile_metric in expected:
            assert cell == str(expected[profile_metric][0])


@pytest.mark.parametrize(
    "conn",
    [
        ("sqlite_sqlalchemy"),
        ("sqlite_dbapi"),
    ],
)
def test_table_profile_warnings_styles(ip_with_connections, tmp_empty, conn):
    ip_with_connections.run_cell(
        f"""
    %%sql {conn}
    CREATE TABLE numbers (rating float,price varchar(50),number int,word varchar(50));
    INSERT INTO numbers VALUES (14.44, '2.48', 82, 'a');
    INSERT INTO numbers VALUES (13.13, '1.50', 93, 'b');
    """
    )
    out = ip_with_connections.run_cell("%sqlcmd profile -t numbers").result
    stats_table_html = out._table_html
    assert "Columns <code>price</code> have a datatype mismatch" in stats_table_html
    assert "td:nth-child(3)" in stats_table_html
    assert "Following statistics are not available in" in stats_table_html


def test_profile_is_numeric():
    assert _is_numeric("123") is True
    assert _is_numeric(None) is False
    assert _is_numeric("abc") is False
    assert _is_numeric("45.6") is True
    assert _is_numeric(100) is True
    assert _is_numeric(True) is False
    assert _is_numeric("NaN") is True
    assert _is_numeric(math.nan) is True


@pytest.mark.parametrize(
    "conn",
    [
        ("sqlite_sqlalchemy"),
        ("sqlite_dbapi"),
    ],
)
def test_table_profile_is_numeric(ip_with_connections, tmp_empty, conn):
    ip_with_connections.run_cell(
        f"""
        %%sql {conn}
        CREATE TABLE people (name varchar(50),age varchar(50),number int,
            country varchar(50),gender_1 varchar(50), gender_2 varchar(50));
        INSERT INTO people VALUES ('joe', '48', 82, 'usa', '0', 'male');
        INSERT INTO people VALUES ('paula', '50', 93, 'uk', '1', 'female');
        """
    )
    out = ip_with_connections.run_cell("%sqlcmd profile -t people").result
    stats_table_html = out._table_html
    assert "td:nth-child(3)" in stats_table_html
    assert "td:nth-child(6)" in stats_table_html
    assert "td:nth-child(7)" not in stats_table_html
    assert "td:nth-child(4)" not in stats_table_html
    assert (
        "Columns <code>age</code><code>gender_1</code> have a datatype mismatch"
        in stats_table_html
    )


@pytest.mark.parametrize(
    "conn, report_fname",
    [
        ("sqlite_sqlalchemy", "test_report.html"),
        ("sqlite_dbapi", "test_report_dbapi.html"),
    ],
)
def test_table_profile_store(ip_with_connections, tmp_empty, conn, report_fname):
    ip_with_connections.run_cell(
        f"""
    %%sql {conn}
    CREATE TABLE test_store (rating, price, number, symbol);
    INSERT INTO test_store VALUES (14.44, 2.48, 82, 'a');
    INSERT INTO test_store VALUES (13.13, 1.50, 93, 'b');
    INSERT INTO test_store VALUES (12.59, 0.20, 98, 'a');
    INSERT INTO test_store VALUES (11.54, 0.41, 89, 'a');
    """
    )

    ip_with_connections.run_cell(
        f"%sqlcmd profile -t test_store --output {report_fname}"
    )

    report = Path(report_fname)
    assert report.is_file()


@pytest.mark.parametrize(
    "conn, report_fname",
    [
        ("sqlite_sqlalchemy", "test_report.html"),
        ("sqlite_dbapi", "test_report_dbapi.html"),
    ],
)
def test_table_profile_store_with_substitution(
    ip_with_connections, tmp_empty, conn, report_fname
):
    ip_with_connections.run_cell(
        f"""
    %%sql {conn}
    CREATE TABLE test_store (rating, price, number, symbol);
    INSERT INTO test_store VALUES (14.44, 2.48, 82, 'a');
    INSERT INTO test_store VALUES (13.13, 1.50, 93, 'b');
    INSERT INTO test_store VALUES (12.59, 0.20, 98, 'a');
    INSERT INTO test_store VALUES (11.54, 0.41, 89, 'a');
    """
    )
    ip_with_connections.user_global_ns["table"] = "test_store"
    ip_with_connections.user_global_ns["output"] = report_fname

    ip_with_connections.run_cell("%sqlcmd profile -t {{table}} --output {{output}}")

    report = Path(report_fname)
    assert report.is_file()


@pytest.mark.parametrize(
    "cell, error_message",
    [
        [
            "%sqlcmd test -t test_numbers",
            "Please use a valid comparator.",
        ],
        [
            "%sqlcmd test --t test_numbers --greater 12",
            "Please pass a column to test.",
        ],
        [
            "%sqlcmd test --table test_numbers --column something --greater 100",
            "Referenced column 'something' not found!",
        ],
    ],
    ids=[
        "no_comparator",
        "no_column",
        "no_column_name",
    ],
)
def test_test_error(ip, cell, error_message):
    ip.run_cell(
        """
    %%sql sqlite://
    CREATE TABLE test_numbers (value);
    INSERT INTO test_numbers VALUES (14);
    INSERT INTO test_numbers VALUES (13);
    INSERT INTO test_numbers VALUES (12);
    INSERT INTO test_numbers VALUES (11);
    """
    )

    with pytest.raises(UsageError) as excinfo:
        ip.run_cell(cell)

    assert excinfo.value.error_type == "UsageError"
    assert str(excinfo.value) == error_message


@pytest.mark.parametrize(
    "arguments", ["--table schema1.table1", "--table table1 --schema schema1"]
)
def test_failing_test_with_schema(ip_empty, sample_schema_with_table, arguments):
    expected_error_message = "The above values do not match your test requirements."

    with pytest.raises(UsageError) as excinfo:
        ip_empty.run_cell(f"%sqlcmd test {arguments} --column x --less-than 2")

    assert expected_error_message in str(excinfo.value)


@pytest.mark.parametrize(
    "arguments", ["--table schema1.table1", "--table table1 --schema schema1"]
)
def test_passing_test_with_schema(ip_empty, sample_schema_with_table, arguments):
    out = ip_empty.run_cell(f"%sqlcmd test {arguments} --column x --less-than 3").result
    assert out is True


@pytest.mark.parametrize(
    "arguments",
    ["--table {{schema}}.{{table}}", "--table {{table}} --schema {{schema}}"],
)
def test_test_with_schema_variable_substitution(
    ip_empty, sample_schema_with_table, arguments
):
    ip_empty.user_global_ns["table"] = "table1"
    ip_empty.user_global_ns["schema"] = "schema1"
    out = ip_empty.run_cell(f"%sqlcmd test {arguments} --column x --less-than 3").result
    assert out is True


def test_test_column_variable_substitution(ip_empty, sample_schema_with_table):
    ip_empty.user_global_ns["column"] = "x"
    out = ip_empty.run_cell(
        "%sqlcmd test --table schema1.table1 --column {{column}} --less-than 3"
    ).result
    assert out is True


@pytest.mark.parametrize(
    "cmds, result",
    [
        (["%sqlcmd snippets"], Message("No snippets stored")),
        (
            [
                """%%sql --save test_snippet --no-execute
SELECT * FROM "test_store" WHERE price >= 1.50
""",
                "%sqlcmd snippets",
            ],
            Table(
                ["Stored snippets"],
                [["test_snippet"]],
            ),
        ),
        (
            [
                """%%sql --save test_snippet --no-execute
SELECT * FROM "test_store" WHERE price >= 1.50
""",
                """%%sql --save test_snippet_a --no-execute
SELECT * FROM "test_snippet" WHERE symbol == 'a'
""",
                "%sqlcmd snippets",
            ],
            Table(
                ["Stored snippets"],
                [["test_snippet"], ["test_snippet_a"]],
            ),
        ),
        (
            [
                """%%sql --save test_snippet --no-execute
SELECT * FROM "test_store" WHERE price >= 1.50
""",
                """%%sql --save test_snippet_a --no-execute
SELECT * FROM "test_snippet" WHERE symbol == 'a'
""",
                """%%sql --save test_snippet_b --no-execute
SELECT * FROM "test_snippet" WHERE symbol == 'b'
""",
                "%sqlcmd snippets",
            ],
            Table(
                ["Stored snippets"],
                [["test_snippet"], ["test_snippet_a"], ["test_snippet_b"]],
            ),
        ),
    ],
)
def test_snippet(test_snippet_ip, cmds, result):
    out = [test_snippet_ip.run_cell(cmd) for cmd in cmds][-1].result
    assert str(out) == str(result)
    assert isinstance(out, type(result))


@pytest.mark.parametrize(
    "precmd, cmd, err_msg",
    [
        (
            None,
            "%sqlcmd snippets invalid",
            (
                "'invalid' is not a snippet. Available snippets are 'high_price', "
                "'high_price_a', and 'high_price_b'."
            ),
        ),
        (
            "%sqlcmd snippets -d high_price_b",
            "%sqlcmd snippets invalid",
            (
                "'invalid' is not a snippet. Available snippets are 'high_price', "
                "and 'high_price_a'."
            ),
        ),
        (
            "%sqlcmd snippets -A high_price",
            "%sqlcmd snippets invalid",
            "'invalid' is not a snippet. There is no available snippet.",
        ),
    ],
)
def test_invalid_snippet(ip_snippets, precmd, cmd, err_msg):
    if precmd:
        ip_snippets.run_cell(precmd)

    with pytest.raises(UsageError) as excinfo:
        ip_snippets.run_cell(cmd)

    assert excinfo.value.error_type == "UsageError"
    assert str(excinfo.value) == err_msg


@pytest.mark.parametrize("arg", ["--delete", "-d"])
def test_delete_saved_key(ip_snippets, arg):
    out = ip_snippets.run_cell(f"%sqlcmd snippets {arg} high_price_a").result
    assert "high_price_a has been deleted.\n" in out
    stored_snippets = out[out.find("Stored snippets") + len("Stored snippets: ") :]
    assert "high_price, high_price_b" in stored_snippets
    assert "high_price_a" not in stored_snippets


def test_delete_saved_key_with_variable_substitution(ip_snippets):
    ip_snippets.user_global_ns["snippet_name"] = "high_price_a"
    out = ip_snippets.run_cell("%sqlcmd snippets --delete {{snippet_name}}").result
    assert "high_price_a has been deleted.\n" in out
    stored_snippets = out[out.find("Stored snippets") + len("Stored snippets: ") :]
    assert "high_price, high_price_b" in stored_snippets
    assert "high_price_a" not in stored_snippets


@pytest.mark.parametrize("arg", ["--delete-force", "-D"])
def test_force_delete(ip_snippets, arg):
    out = ip_snippets.run_cell(f"%sqlcmd snippets {arg} high_price").result
    assert (
        "high_price has been deleted.\nhigh_price_a, "
        "high_price_b depend on high_price\n" in out
    )
    stored_snippets = out[out.find("Stored snippets") + len("Stored snippets: ") :]
    assert "high_price_a, high_price_b" in stored_snippets
    assert "high_price," not in stored_snippets


def test_force_delete_with_variable_substitution(ip_snippets):
    ip_snippets.user_global_ns["snippet_name"] = "high_price"
    out = ip_snippets.run_cell(
        "%sqlcmd snippets --delete-force {{snippet_name}}"
    ).result
    assert (
        "high_price has been deleted.\nhigh_price_a, "
        "high_price_b depend on high_price\n" in out
    )
    stored_snippets = out[out.find("Stored snippets") + len("Stored snippets: ") :]
    assert "high_price_a, high_price_b" in stored_snippets
    assert "high_price," not in stored_snippets


@pytest.mark.parametrize("arg", ["--delete-force-all", "-A"])
def test_force_delete_all(ip_snippets, arg):
    out = ip_snippets.run_cell(f"%sqlcmd snippets {arg} high_price").result
    assert "high_price_a, high_price_b, high_price has been deleted" in out
    assert "There are no stored snippets" in out


def test_force_delete_all_with_variable_substitution(ip_snippets):
    ip_snippets.user_global_ns["snippet_name"] = "high_price"
    out = ip_snippets.run_cell(
        "%sqlcmd snippets --delete-force-all {{snippet_name}}"
    ).result
    assert "high_price_a, high_price_b, high_price has been deleted" in out
    assert "There are no stored snippets" in out


@pytest.mark.parametrize("arg", ["--delete-force-all", "-A"])
def test_force_delete_all_child_query(ip_snippets, arg):
    ip_snippets.run_cell(
        """
%%sql --save high_price_b_child --no-execute
SELECT *
FROM "high_price_b"
WHERE symbol == 'b'
LIMIT 3
"""
    )
    out = ip_snippets.run_cell(f"%sqlcmd snippets {arg} high_price_b").result
    assert "high_price_b_child, high_price_b has been deleted" in out
    stored_snippets = out[out.find("Stored snippets") + len("Stored snippets: ") :]
    assert "high_price, high_price_a" in stored_snippets
    assert "high_price_b," not in stored_snippets
    assert "high_price_b_child" not in stored_snippets


@pytest.mark.parametrize(
    "arg",
    [
        "--delete",
        "-d",
    ],
)
def test_delete_snippet_error(ip_snippets, arg):
    with pytest.raises(UsageError) as excinfo:
        ip_snippets.run_cell(f"%sqlcmd snippets {arg} high_price")

    assert excinfo.value.error_type == "UsageError"
    assert (
        str(excinfo.value) == "The following tables are dependent on high_price: "
        "high_price_a, high_price_b.\nPass --delete-force to only "
        "delete high_price.\nPass --delete-force-all to delete "
        "high_price_a, high_price_b and high_price"
    )


@pytest.mark.parametrize(
    "arg",
    [
        "--delete",
        "-d",
        "--delete-force-all",
        "-A",
        "--delete-force",
        "-D",
    ],
)
def test_delete_invalid_snippet(arg, ip_snippets):
    with pytest.raises(UsageError) as excinfo:
        ip_snippets.run_cell(f"%sqlcmd snippets {arg} non_existent_snippet")

    assert excinfo.value.error_type == "UsageError"
    assert str(excinfo.value) == "No such saved snippet found : non_existent_snippet"


@pytest.mark.parametrize("arg", ["--delete-force", "-D"])
def test_delete_snippet_when_dependency_force_deleted(ip_snippets, arg):
    ip_snippets.run_cell(f"%sqlcmd snippets {arg} high_price")
    out = ip_snippets.run_cell("%sqlcmd snippets --delete high_price_a").result
    assert "high_price_a has been deleted.\nStored snippets: high_price_b" in out


def test_view_snippet_variable_substitution(ip_snippets):
    ip_snippets.user_global_ns["snippet_name"] = "test_snippet"
    ip_snippets.run_cell(
        """%%sql --save {{snippet_name}} --no-execute
SELECT * FROM "test_store" WHERE price >= 1.50
"""
    )

    out = ip_snippets.run_cell("%sqlcmd snippets {{snippet_name}}").result
    assert 'SELECT * FROM "test_store" WHERE price >= 1.50' in out


@pytest.mark.parametrize(
    "arguments", ["--table schema1.table1", "--table table1 --schema schema1"]
)
def test_explore_with_schema(ip_empty, sample_schema_with_table, arguments):
    expected_rows = ['"x": 1', '"y": "one"', '"x": 2', '"y": "two"']

    out = ip_empty.run_cell(f"%sqlcmd explore {arguments}").result
    assert isinstance(out, TableWidget)
    assert [row in out._repr_html_() for row in expected_rows]


@pytest.mark.parametrize(
    "arguments",
    ["--table {{schema}}.{{table}}", "--table {{table}} --schema {{schema}}"],
)
def test_explore_with_schema_variable_substitution(
    ip_empty, sample_schema_with_table, arguments
):
    expected_rows = ['"x": 1', '"y": "one"', '"x": 2', '"y": "two"']
    ip_empty.user_global_ns["table"] = "table1"
    ip_empty.user_global_ns["schema"] = "schema1"
    out = ip_empty.run_cell(f"%sqlcmd explore {arguments}").result
    assert isinstance(out, TableWidget)
    assert [row in out._repr_html_() for row in expected_rows]


@pytest.mark.parametrize(
    "file_content, stored_conns",
    [
        (
            """[conn1]
drivername = sqlite
""",
            [{"name": "conn1", "driver": "sqlite"}],
        ),
        (
            """[conn1]
drivername = sqlite

[conn2]
drivername = sqlite

[conn3]
drivername = duckdb
""",
            [
                {"name": "conn1", "driver": "sqlite"},
                {"name": "conn2", "driver": "sqlite"},
                {"name": "conn3", "driver": "duckdb"},
            ],
        ),
        ("", []),
    ],
)
def test_connect_with_connections_ini(tmp_empty, ip_empty, file_content, stored_conns):
    Path("connections.ini").write_text(file_content)
    ip_empty.run_cell("%load_ext sql")
    ip_empty.run_cell("%config SqlMagic.dsn_filename = './connections.ini'")
    connector_widget = ip_empty.run_cell("%sqlcmd connect").result
    assert isinstance(connector_widget, ConnectorWidget)
    assert connector_widget.stored_connections == stored_conns


def test_connect_when_no_connections_ini(tmp_empty, ip_empty):
    ip_empty.run_cell("%load_ext sql")
    ip_empty.run_cell("%config SqlMagic.dsn_filename = './connections.ini'")
    connector_widget = ip_empty.run_cell("%sqlcmd connect").result
    assert isinstance(connector_widget, ConnectorWidget)
    assert connector_widget.stored_connections == []
