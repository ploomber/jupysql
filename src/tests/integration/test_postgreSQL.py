import pyodbc
import pytest
from matplotlib import pyplot as plt
from IPython.core.error import UsageError
from dockerctx import new_container
from contextlib import contextmanager
import pandas as pd
import urllib.request
import requests
from sql.ggplot import ggplot, aes, geom_histogram, facet_wrap, geom_boxplot
from matplotlib.testing.decorators import image_comparison, _cleanup_cm
from sql.connection import CustomConnection, CustomSession
from IPython.core.error import UsageError

def test_meta_cmd_display(ip_with_postgreSQL, test_table_name_dict):
    out = ip_with_postgreSQL.run_cell("%sql \d")  # noqa: W605
    assert len(out.result) > 0
    assert (
        "public",
        test_table_name_dict["taxi"],
        "table",
        "ploomber_app",
    ) in out.result


def test_auto_commit_mode_on(ip_with_postgreSQL, capsys):
    ip_with_postgreSQL.run_cell("%config SqlMagic.autocommit=True")
    out_after_creating = ip_with_postgreSQL.run_cell("%sql CREATE DATABASE new_db")
    out_all_dbs = ip_with_postgreSQL.run_cell("%sql \l").result  # noqa: W605
    out, _ = capsys.readouterr()
    assert out_after_creating.error_in_exec is None
    assert any(row[0] == "new_db" for row in out_all_dbs)
    assert "CREATE DATABASE cannot run inside a transaction block" not in out


def test_postgres_error(ip_empty, postgreSQL_config_incorrect_pwd):
    alias, url = postgreSQL_config_incorrect_pwd

    # Select database engine
    out = ip_empty.run_cell("%sql " + url + " --alias " + alias)
    assert "Review our DB connection via URL strings guide" in str(out.error_in_exec)
    assert "Original error message from DB driver" in str(out.error_in_exec)
    assert (
        "If you need help solving this issue, "
        "send us a message: https://ploomber.io/community" in str(out.error_in_exec)
    )

def test_query_count(ip_with_postgreSQL, test_table_name_dict):
    # PostgreSQL doesn't have LIMIT
    out = ip_with_postgreSQL.run_line_magic(
        "sql",
        f"""
        SELECT TOP 3 *
        FROM {test_table_name_dict['taxi']}
        """,
    )

    assert len(out) == 3


def test_cte(ip_with_postgreSQL, test_table_name_dict):
    ip_with_postgreSQL.run_cell(
        f"%sql --save taxi_subset --no-execute \
        SELECT TOP 3 * FROM {test_table_name_dict['taxi']} "
    )
    out_query_with_save_arg = ip_with_postgreSQL.run_cell(
        "%sql --with taxi_subset SELECT * FROM taxi_subset"
    )
    assert len(out_query_with_save_arg.result) == 3


def test_create_table_with_indexed_df(ip_with_postgreSQL, test_table_name_dict):
    # MSSQL gives error if DB doesn't exist
    try:
        ip_with_postgreSQL.run_cell(
            f"%sql DROP TABLE {test_table_name_dict['new_table_from_df']}"
        )
    except pyodbc.ProgrammingError as e:
        print(f"Error: {e}")

    # Prepare DF
    ip_with_postgreSQL.run_cell(
        f"""results = %sql\
                    SELECT TOP 15 *\
                    FROM {test_table_name_dict['taxi']}
                    """
    )
    ip_with_postgreSQL.run_cell(
        f"{test_table_name_dict['new_table_from_df']} = results.DataFrame()"
    )
    # Create table from DF
    persist_out = ip_with_postgreSQL.run_cell(
        f"%sql --persist {test_table_name_dict['new_table_from_df']}"
    )
    query_out = ip_with_postgreSQL.run_cell(
        f"%sql SELECT * FROM {test_table_name_dict['new_table_from_df']}"
    )
    assert persist_out.error_in_exec is None and query_out.error_in_exec is None
    assert len(query_out.result) == 15


@pytest.mark.parametrize(
    "cell",
    [
        ("%sqlplot histogram --table plot_something --column x"),
        ("%sqlplot hist --table plot_something --column x"),
        ("%sqlplot histogram --table plot_something --column x --bins 10"),
    ],
    ids=[
        "histogram",
        "hist",
        "histogram-bins",
    ],
)
def test_sqlplot_histogram(ip_with_postgreSQL, cell):
    # clean current Axes
    plt.cla()

    ip_with_postgreSQL.run_cell(
        "%sql --save plot_something_subset"
        " --no-execute SELECT TOP 3 * from plot_something "
    )
    out = ip_with_postgreSQL.run_cell(cell)

    assert type(out.result).__name__ in {"Axes", "AxesSubplot"}


@pytest.mark.parametrize(
    "cell",
    [
        "%sqlplot boxplot --table plot_something --column x",
        "%sqlplot box --table plot_something --column x",
        "%sqlplot boxplot --table plot_something --column x --orient h",
        "%sqlplot boxplot --with plot_something_subset --table "
        "plot_something_subset --column x",
    ],
    ids=[
        "boxplot",
        "box",
        "boxplot-horizontal",
        "boxplot-with",
    ],
)
def test_sqlplot_boxplot(ip_with_postgreSQL, cell):
    # clean current Axes
    plt.cla()
    ip_with_postgreSQL.run_cell(
        "%sql --save plot_something_subset"
        " --no-execute SELECT TOP 3 * from plot_something"
    )

    out = ip_with_postgreSQL.run_cell(cell)

    assert type(out.result).__name__ in {"Axes", "AxesSubplot"}

def test_unsupported_function(ip_with_postgreSQL, test_table_name_dict):
    # clean current Axes
    plt.cla()
    out = ip_with_postgreSQL.run_cell(
        f"%sqlplot boxplot --table " f"{test_table_name_dict['taxi']} --column x"
    )
    assert isinstance(out.error_in_exec, UsageError)
    assert "Ensure that percentile_disc function is available" in str(out.error_in_exec)
    assert (
        "If you need help solving this issue, "
        "send us a message: https://ploomber.io/community" in str(out.error_in_exec)
    )