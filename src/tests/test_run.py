from unittest.mock import Mock

import pandas
import polars
import pytest

from sql.run import (
    run,
    handle_postgres_special,
    is_postgres_or_redshift,
    select_df_type,
)


@pytest.fixture
def mock_config():
    class Config:
        autopandas = None
        autopolars = None
        autocommit = None
        feedback = True

    return Config


@pytest.fixture
def mock_config_is_pandas(mock_config):
    mock_config.autopandas = True
    mock_config.autopolars = False

    return mock_config


@pytest.fixture
def mock_config_is_polars(mock_config):
    mock_config.autopandas = False
    mock_config.autopolars = True

    return mock_config


@pytest.fixture
def mock_result_set():
    class ResultSet:
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


def test_handle_postgres_special(clean_conns):
    with pytest.raises(ImportError):
        handle_postgres_special(clean_conns, "\\")


def test_select_df_type_is_pandas(monkeypatch, mock_config_is_pandas, mock_result_set):
    mock_select_df_type = pandas.DataFrame()
    monkeypatch.setattr("sql.run.select_df_type", mock_select_df_type)
    result = select_df_type(mock_result_set, mock_config_is_pandas)
    assert isinstance(result, pandas.DataFrame)


def test_select_df_type_is_polars(monkeypatch, mock_config_is_polars, mock_result_set):
    mock_select_df_type = polars.DataFrame()
    monkeypatch.setattr("sql.run.select_df_type", mock_select_df_type)
    result = select_df_type(mock_result_set, mock_config_is_polars)
    assert isinstance(result, polars.DataFrame)


def test_select_df_type_is_none(monkeypatch, mock_config, mock_result_set):
    mock_select_df_type = mock_result_set
    monkeypatch.setattr("sql.run.select_df_type", mock_select_df_type)
    result = select_df_type(mock_result_set, mock_config)
    assert isinstance(result, type(mock_result_set))


def test_sql_begin_exception(clean_conns, mock_config):
    with pytest.raises(Exception):
        run(clean_conns, "BEGIN", mock_config, "user_namespace")


def test_sql_empty(mock_conns, mock_config):
    assert (
        run(mock_conns, "", mock_config, "user_namespace")
        == "Connected: %s" % mock_conns.name
    )


def test_handle_postgres_special_is_called(
    monkeypatch,
    mock_conns,
    mock_config,
):
    mock_handle_postgres_special = Mock()
    monkeypatch.setattr("sql.run.handle_postgres_special", mock_handle_postgres_special)
    monkeypatch.setattr("sql.run._commit", Mock())
    monkeypatch.setattr("sql.run.interpret_rowcount", Mock())
    monkeypatch.setattr("sql.run.ResultSet", Mock())

    run(mock_conns, "\\", mock_config, "user_namespace")

    mock_handle_postgres_special.assert_called()
    mock_handle_postgres_special.assert_called_once_with(mock_conns, "\\")
