import pyodbc
import pytest
from matplotlib import pyplot as plt


def test_query_count(ip_with_MSSQL):
    # MSSQL doesn't have LIMIT
    out = ip_with_MSSQL.run_line_magic(
        "sql",
        """
        SELECT TOP 3 *
        FROM taxi
        """,
    )

    assert len(out) == 3


@pytest.mark.xfail(reason="Known sqlglot issue, addressing in: jupysql/issues/307")
def test_cte(ip_with_MSSQL):
    ip_with_MSSQL.run_cell(
        "%sql --save taxi_subset --no-execute \
        SELECT TOP 3 * FROM taxi "
    )
    out_query_with_save_arg = ip_with_MSSQL.run_cell(
        "%sql --with taxi_subset SELECT * FROM taxi_subset"
    )
    assert len(out_query_with_save_arg.result) == 3


def test_create_table_with_indexed_df(ip_with_MSSQL):
    # MSSQL gives error if DB doesn't exist
    try:
        ip_with_MSSQL.run_cell("%sql DROP TABLE new_table_from_df")
    except pyodbc.ProgrammingError as e:
        print(f"Error: {e}")

    # Prepare DF
    ip_with_MSSQL.run_cell(
        """results = %sql\
                    SELECT TOP 15 *\
                    FROM taxi
                    """
    )
    ip_with_MSSQL.run_cell("new_table_from_df = results.DataFrame()")
    # Create table from DF
    persist_out = ip_with_MSSQL.run_cell("%sql --persist new_table_from_df")
    query_out = ip_with_MSSQL.run_cell("%sql SELECT * FROM new_table_from_df")
    assert persist_out.error_in_exec is None and query_out.error_in_exec is None
    assert len(query_out.result) == 15


@pytest.mark.xfail(reason="Known sqlglot issue, addressing in: jupysql/issues/307")
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
def test_sqlplot_histogram(ip_with_MSSQL, cell):
    # clean current Axes
    plt.cla()

    ip_with_MSSQL.run_cell(
        "%sql --save plot_something_subset"
        " --no-execute SELECT TOP 3 * from plot_something "
    )
    out = ip_with_MSSQL.run_cell(cell)

    assert type(out.result).__name__ in {"Axes", "AxesSubplot"}


@pytest.mark.xfail(reason="Known sqlglot issue, addressing in: jupysql/issues/307")
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
def test_sqlplot_boxplot(ip_with_MSSQL, cell):
    # clean current Axes
    plt.cla()
    ip_with_MSSQL.run_cell(
        "%sql --save plot_something_subset"
        " --no-execute SELECT TOP 3 * from plot_something"
    )

    out = ip_with_MSSQL.run_cell(cell)

    assert type(out.result).__name__ in {"Axes", "AxesSubplot"}
