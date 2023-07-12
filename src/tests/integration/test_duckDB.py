from unittest.mock import Mock
import logging

import polars as pl
import pandas as pd
import pytest

from sql.connection import Connection
from sql.run import ResultSet


@pytest.fixture
def ip_duckdb_native(ip_empty):
    ip_empty.run_cell("import duckdb; conn = duckdb.connect()")
    ip_empty.run_cell("%sql conn --alias duck")
    yield ip_empty


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


# TODO: test the case where you already fetched some resuults because
# in that sceenario the results will be empty
# TODO: test with autopanas
# TODO: fix resultset fetchall
# TODO: warn when duckdb + autopandas or calling DataFrame/PolarsDataFrame


@pytest.mark.parametrize(
    "method, expected_type, expected_native_method",
    [
        ("DataFrame", pd.DataFrame, "df"),
        ("PolarsDataFrame", pl.DataFrame, "pl"),
    ],
)
def test_can_convert_to_bears_natively(
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
    monkeypatch.setattr(results, "sqlaproxy", mock)

    out = ip_duckdb_native.run_cell(f"results.{method}()")

    mock.execute.assert_called_once_with("SELECT * FROM weather")
    getattr(mock, expected_native_method).assert_called_once_with()
    assert isinstance(out.result, expected_type)
    assert out.result.shape == (2, 2)
