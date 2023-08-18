import pytest
from matplotlib import pyplot as plt


def test_query_count(ip_with_clickhouse, test_table_name_dict):
    out = ip_with_clickhouse.run_line_magic(
        "sql",
        f"""
        SELECT *
        FROM {test_table_name_dict['taxi']}
        LIMIT 3;
        """,
    )

    assert len(out) == 3


@pytest.mark.xfail(reason="issue with plotting from snippet #811")
@pytest.mark.parametrize(
    "cell",
    [
        (
            "%sqlplot histogram --with plot_something_subset \
            --table plot_something_subset --column x"
        ),
        (
            "%sqlplot hist --with plot_something_subset \
            --table plot_something_subset --column x"
        ),
        (
            "%sqlplot histogram --with plot_something_subset \
            --table plot_something_subset --column x --bins 10"
        ),
    ],
    ids=[
        "histogram",
        "hist",
        "histogram-bins",
    ],
)
def test_sqlplot_histogram(ip_with_clickhouse, cell, request, test_table_name_dict):
    # clean current Axes
    plt.cla()

    ip_with_clickhouse.run_cell(
        f"%sql --save plot_something_subset\
         --no-execute SELECT * from {test_table_name_dict['plot_something']} \
         LIMIT 3"
    )
    out = ip_with_clickhouse.run_cell(cell)

    assert type(out.result).__name__ in {"Axes", "AxesSubplot"}
