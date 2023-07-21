import sqlite3
import warnings
import logging
from unittest.mock import Mock

from IPython.core.error import UsageError
import pandas
import polars
import pytest
from sqlalchemy import create_engine
import duckdb

from sql.connection import Connection, DBAPIConnection
from sql.run.run import (
    run,
    is_postgres_or_redshift,
    select_df_type,
    set_sqlalchemy_autocommit_option,
    display_affected_rowcount,
)
from sql.run.pgspecial import handle_postgres_special
from sql.run.resultset import ResultSet


@pytest.fixture
def mock_conns():
    conn = Connection(Mock())
    conn.connection_sqlalchemy.execution_options.side_effect = ValueError
    return conn


class Config:
    autopandas = None
    autopolars = None
    autocommit = True
    feedback = True
    polars_dataframe_kwargs = {}
    style = "DEFAULT"
    autolimit = 0
    displaylimit = 10


class ConfigPandas(Config):
    autopandas = True
    autopolars = False


class ConfigPolars(Config):
    autopandas = False
    autopolars = True


@pytest.fixture
def pytds_conns(mock_conns):
    mock_conns._dialect = "mssql+pytds"
    return mock_conns


@pytest.fixture
def mock_resultset():
    class ResultSet:
        def __init__(self, *args, **kwargs):
            pass

        @classmethod
        def DataFrame(cls):
            return pandas.DataFrame()

        @classmethod
        def PolarsDataFrame(cls):
            return polars.DataFrame()

    return ResultSet


@pytest.mark.parametrize(
    "dialect",
    [
        "postgres",
        "redshift",
    ],
)
def test_is_postgres_or_redshift(dialect):
    assert is_postgres_or_redshift(dialect) is True


def test_handle_postgres_special(mock_conns):
    with pytest.raises(UsageError) as excinfo:
        handle_postgres_special(mock_conns, "\\")

    assert "pgspecial not installed" in str(excinfo.value)


def test_set_sqlalchemy_autocommit_option(mock_conns, caplog):
    caplog.set_level(logging.DEBUG)

    output = set_sqlalchemy_autocommit_option(mock_conns, Config)

    with warnings.catch_warnings():
        warnings.simplefilter("error")

    assert "The database driver doesn't support such " in caplog.records[0].msg
    assert output is True


def test_pytds_autocommit(pytds_conns):
    with warnings.catch_warnings(record=True) as w:
        output = set_sqlalchemy_autocommit_option(pytds_conns, Config)
        assert (
            str(w[-1].message)
            == "Autocommit is not supported for pytds, thus is automatically disabled"
        )
        assert output is False


def test_select_df_type_is_pandas(mock_resultset):
    output = select_df_type(mock_resultset, ConfigPandas)
    assert isinstance(output, pandas.DataFrame)


def test_select_df_type_is_polars(mock_resultset):
    output = select_df_type(mock_resultset, ConfigPolars)
    assert isinstance(output, polars.DataFrame)


def test_sql_starts_with_begin(mock_conns):
    with pytest.raises(UsageError, match="does not support transactions") as excinfo:
        run(mock_conns, "BEGIN", Config)

    assert excinfo.value.error_type == "RuntimeError"


def test_sql_is_empty(mock_conns):
    assert run(mock_conns, "  ", Config) == "Connected: %s" % mock_conns.name


@pytest.mark.parametrize(
    "n, message",
    [
        [1, "1 rows affected.\n"],
        [0, ""],
    ],
)
def test_display_affected_rowcount(capsys, n, message):
    display_affected_rowcount(n)
    captured = capsys.readouterr()
    assert captured.out == message


@pytest.mark.parametrize(
    "connection",
    [
        Connection(create_engine("duckdb://")),
        Connection(create_engine("sqlite://")),
        DBAPIConnection(duckdb.connect()),
        DBAPIConnection(sqlite3.connect("")),
    ],
)
@pytest.mark.parametrize(
    "config, expected_type",
    [
        [Config, ResultSet],
        [ConfigPandas, pandas.DataFrame],
        [ConfigPolars, polars.DataFrame],
    ],
)
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT 1; SELECT 2;",
    ],
    ids=["single", "multiple"],
)
def test_run(connection, config, expected_type, sql):
    out = run(connection, sql, config)
    assert isinstance(out, expected_type)


def test_run_calls_commit():
    pass
