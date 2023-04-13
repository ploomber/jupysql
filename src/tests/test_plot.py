from typing import Iterator
from collections.abc import Mapping

import numpy as np
from matplotlib import cbook
from sql import plot
from sql.connection import Connection
from pathlib import Path
import pytest


class DictOfFloats(Mapping):
    def __init__(self, data) -> None:
        self._data = data

    def __eq__(self, other: object) -> bool:
        same_keys = set(self._data) == set(other)

        if not same_keys:
            return False

        for key, value in self._data.items():
            isclose = np.isclose(value, other[key])

            if isinstance(isclose, np.bool_):
                if not isclose:
                    return False
            elif not all(isclose):
                return False

        return True

    def __iter__(self) -> Iterator[str]:
        for key in self._data:
            yield key

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, key: str):
        return self._data[key]

    def __repr__(self) -> str:
        return repr(self._data)


def test_boxplot_stats(chinook_db, ip_empty):
    ip_empty.run_cell("%sql duckdb://")
    ip_empty.run_cell("%sql INSTALL 'sqlite_scanner';")
    ip_empty.run_cell("%sql commit")
    ip_empty.run_cell("%sql LOAD 'sqlite_scanner';")
    ip_empty.run_cell(f"%sql CALL sqlite_attach({chinook_db!r});")

    res = ip_empty.run_cell("%sql SELECT * FROM Invoice").result
    X = res.DataFrame().Total
    expected = cbook.boxplot_stats(X)
    result = plot._boxplot_stats(Connection.current, "Invoice", "Total")

    assert DictOfFloats(result) == DictOfFloats(expected[0])


def test_boxplot_stats_exception(chinook_db, ip_empty):
    ip_empty.run_cell("%sql duckdb://")
    ip_empty.run_cell("%sql INSTALL 'sqlite_scanner';")
    ip_empty.run_cell("%sql commit")
    ip_empty.run_cell("%sql LOAD 'sqlite_scanner';")
    ip_empty.run_cell(f"%sql CALL sqlite_attach({chinook_db!r});")

    res = ip_empty.run_cell("%sql SELECT * FROM Invoice").result

    X = res.DataFrame().Total
    cbook.boxplot_stats(X)
    with pytest.raises(
        BaseException, match="whis must be a float or list of percentiles.*"
    ):
        plot._boxplot_stats(
            Connection.current,
            "Invoice",
            "Total",
            "Not a float or list of percentiles whis param",
        )


# Test internal plot function e.g.
def test_internal_histogram_nulls(tmp_empty, ip):
    Path("data.csv").write_text("name,age\nDan,33\nBob,19\nSheri,")
    ip.run_cell("%sql duckdb://")
    ip.run_cell(
        """%%sql --save test_dataset --no-execute
SELECT *
FROM data.csv
"""
    )
    out = ip.run_cell(
        "%sqlplot histogram --table data.csv --column age --table data.csv"
    )
    assert type(out.result).__name__ in {"Axes", "AxesSubplot"}
