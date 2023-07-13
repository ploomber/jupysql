from unittest.mock import Mock
import logging

from sqlalchemy import text
import polars as pl
import pandas as pd
import pytest

from sql.connection import Connection
from sql.run import ResultSet
from sql import connection
from sql.warnings import JupySQLDataFramePerformanceWarning


@pytest.fixture
def ip_duckdb_native(ip_empty_testing):
    ip_empty_testing.run_cell("import duckdb; conn = duckdb.connect()")
    ip_empty_testing.run_cell("%sql conn --alias duck")
    yield ip_empty_testing
    ip_empty_testing.run_cell("conn.close()")


def test_auto_commit_mode_on(ip_with_duckDB, caplog):
    with caplog.at_level(logging.DEBUG):
        ip_with_duckDB.run_cell("%config SqlMagic.autocommit=True")
        ip_with_duckDB.run_cell("%sql CREATE TABLE weather4 (city VARCHAR,);")
    assert caplog.record_tuples == [
        (
            "root",
            logging.DEBUG,
            "The database driver doesn't support such AUTOCOMMIT "
            "execution option\nPerhaps you can try running a manual "
            "COMMIT command\nMessage from the database driver\n\t"
            "Exception:  'duckdb.DuckDBPyConnection' object has no attribute"
            " 'set_isolation_level'\n",
        )
    ]


def test_auto_commit_mode_off(ip_with_duckDB, caplog):
    with caplog.at_level(logging.DEBUG):
        ip_with_duckDB.run_cell("%config SqlMagic.autocommit=False")
        ip_with_duckDB.run_cell("%sql CREATE TABLE weather (city VARCHAR,);")
    # Check there is no message gets printed
    assert caplog.record_tuples == []
    # Check the tables is created
    tables_out = ip_with_duckDB.run_cell("%sql SHOW TABLES;").result
    assert any("weather" == table[0] for table in tables_out)


def test_native_connection_sets_right_dialect(ip_duckdb_native):
    assert Connection.current.is_custom_connection()
    assert Connection.current.dialect == "duckdb"


@pytest.mark.parametrize(
    "method, expected_type, expected_native_method",
    [
        ("DataFrame", pd.DataFrame, "df"),
        ("PolarsDataFrame", pl.DataFrame, "pl"),
    ],
)
def test_converts_to_data_frames_natively(
    monkeypatch,
    ip_duckdb_native,
    method,
    expected_type,
    expected_native_method,
):
    ip_duckdb_native.run_cell("%sql CREATE TABLE weather (city VARCHAR, temp_lo INT);")
    ip_duckdb_native.run_cell("%sql INSERT INTO weather VALUES ('San Francisco', 46);")
    ip_duckdb_native.run_cell("%sql INSERT INTO weather VALUES ('NYC', 20);")
    ip_duckdb_native.run_cell("results = %sql SELECT * FROM weather")

    results = ip_duckdb_native.run_cell("results").result

    mock = Mock(wraps=results.sqlaproxy)
    monkeypatch.setattr(results, "_sqlaproxy", mock)

    out = ip_duckdb_native.run_cell(f"results.{method}()")

    mock.execute.assert_called_once_with("SELECT * FROM weather")
    getattr(mock, expected_native_method).assert_called_once_with()
    assert isinstance(out.result, expected_type)
    assert out.result.shape == (2, 2)


@pytest.mark.parametrize(
    "conversion_cell, expected_type",
    [
        ("%config SqlMagic.autopandas = True", pd.DataFrame),
        ("%config SqlMagic.autopolars = True", pl.DataFrame),
    ],
    ids=[
        "autopandas_on",
        "autopolars_on",
    ],
)
def test_auto_data_frame_config(
    ip_duckdb_native,
    conversion_cell,
    expected_type,
):
    ip_duckdb_native.run_cell(conversion_cell)
    ip_duckdb_native.run_cell("%sql CREATE TABLE weather (city VARCHAR, temp_lo INT);")
    ip_duckdb_native.run_cell("%sql INSERT INTO weather VALUES ('San Francisco', 46);")
    ip_duckdb_native.run_cell("%sql INSERT INTO weather VALUES ('NYC', 20);")
    df = ip_duckdb_native.run_cell("%sql SELECT * FROM weather").result
    assert isinstance(df, expected_type)
    assert df.shape == (2, 2)


@pytest.mark.parametrize(
    "config",
    [
        "%config SqlMagic.autopandas = True",
        "%config SqlMagic.autopandas = False",
    ],
    ids=[
        "autopandas_on",
        "autopandas_off",
    ],
)
@pytest.mark.parametrize(
    "sql, tables",
    [
        ["%sql SELECT * FROM weather; SELECT * FROM weather;", ["weather"]],
        [
            "%sql CREATE TABLE names (name VARCHAR,); SELECT * FROM weather;",
            ["weather", "names"],
        ],
        [
            (
                "%sql CREATE TABLE names (city VARCHAR,);"
                "CREATE TABLE more_names (city VARCHAR,);"
                "INSERT INTO names VALUES ('NYC');"
                "SELECT * FROM names UNION ALL SELECT * FROM more_names;"
            ),
            ["weather", "names", "more_names"],
        ],
    ],
    ids=[
        "multiple_selects",
        "multiple_statements",
        "multiple_tables_created",
    ],
)
def test_multiple_statements(ip_empty, config, sql, tables):
    ip_empty.run_cell("%sql duckdb://")
    ip_empty.run_cell(config)

    ip_empty.run_cell("%sql CREATE TABLE weather (city VARCHAR,);")
    ip_empty.run_cell("%sql INSERT INTO weather VALUES ('NYC');")
    ip_empty.run_cell("%sql SELECT * FROM weather;")

    out = ip_empty.run_cell(sql)
    out_tables = ip_empty.run_cell("%sqlcmd tables")

    assert out.error_in_exec is None

    if config == "%config SqlMagic.autopandas = True":
        assert out.result.to_dict() == {"city": {0: "NYC"}}
    else:
        assert out.result.dict() == {"city": ("NYC",)}

    assert set(tables) == set(r[0] for r in out_tables.result._table.rows)


def test_dataframe_returned_only_if_last_statement_is_select(ip_empty):
    ip_empty.run_cell("%sql duckdb://")
    ip_empty.run_cell("%config SqlMagic.autopandas=True")
    connection.Connection.connections["duckdb://"].engine.raw_connection = Mock(
        side_effect=ValueError("some error")
    )

    out = ip_empty.run_cell(
        "%sql CREATE TABLE a (c VARCHAR,); CREATE TABLE b (c VARCHAR,);"
    )

    assert out.error_in_exec is None


@pytest.mark.parametrize(
    "sql",
    [
        (
            "%sql CREATE TABLE a (x INT,); CREATE TABLE b (x INT,); "
            "INSERT INTO a VALUES (1,); INSERT INTO b VALUES(2,); "
            "SELECT * FROM a UNION ALL SELECT * FROM b;"
        ),
        """\
%%sql
CREATE TABLE a (x INT,);
CREATE TABLE b (x INT,);
INSERT INTO a VALUES (1,);
INSERT INTO b VALUES(2,);
SELECT * FROM a UNION ALL SELECT * FROM b;
""",
    ],
)
def test_commits_all_statements(ip_empty, sql):
    ip_empty.run_cell("%sql duckdb://")
    out = ip_empty.run_cell(sql)
    assert out.error_in_exec is None
    assert out.result.dict() == {"x": (1, 2)}


def test_resultset_uses_native_duckdb_df(ip_empty):
    from sqlalchemy import create_engine
    from sql.connection import Connection

    engine = create_engine("duckdb://")
    session = engine.connect()

    session.execute(text("CREATE TABLE a (x INT,);"))
    session.execute(text("INSERT INTO a(x) VALUES (10),(20),(30);"))

    sql = text("SELECT * FROM a")

    # this breaks if there's an open results set
    session.execute(sql).fetchall()

    results = session.execute(sql)

    Connection.set(engine, displaycon=False)

    results.fetchmany = Mock(wraps=results.fetchmany)

    mock = Mock()
    mock.displaylimit = 1
    mock.autolimit = 0

    result_set = ResultSet(results, mock, statement=sql, conn=Mock())

    df = result_set.DataFrame()

    assert isinstance(df, pd.DataFrame)
    assert df.to_dict() == {"x": {0: 10, 1: 20, 2: 30}}

    results.fetchmany.assert_called_once_with(size=2)


@pytest.mark.parametrize("method", ["DataFrame", "PolarsDataFrame"])
def test_warn_when_using_sqlalchemy_and_converting_to_dataframe(ip_empty, method):
    ip_empty.run_cell("%sql duckdb://")
    df = pd.DataFrame(range(1000))  # noqa

    data = ip_empty.run_cell("%sql SELECT * FROM df;").result

    with pytest.warns(JupySQLDataFramePerformanceWarning) as record:
        getattr(data, method)()

    assert len(record) == 1
