from unittest.mock import Mock, call

from sqlalchemy import create_engine, text
from pathlib import Path


import pytest
import pandas as pd
import polars as pl
import sqlalchemy

from sql.run import ResultSet
from sql import run as run_module


@pytest.fixture
def config():
    config = Mock()
    config.displaylimit = 5
    config.autolimit = 100
    return config


@pytest.fixture
def result():
    df = pd.DataFrame({"x": range(3)})  # noqa
    engine = sqlalchemy.create_engine("duckdb://")

    conn = engine.connect()
    result = conn.execute(sqlalchemy.text("select * from df"))
    yield result
    conn.close()


@pytest.fixture
def result_set(result, config):
    return ResultSet(result, config, statement=None, conn=Mock())


def test_resultset_getitem(result_set):
    assert result_set[0] == (0,)
    assert result_set[0:2] == [(0,), (1,)]


def test_resultset_dict(result_set):
    assert result_set.dict() == {"x": (0, 1, 2)}


def test_resultset_len(result_set):
    assert len(result_set) == 3


def test_resultset_dicts(result_set):
    assert list(result_set.dicts()) == [{"x": 0}, {"x": 1}, {"x": 2}]


def test_resultset_dataframe(result_set, monkeypatch):
    monkeypatch.setattr(run_module.Connection, "current", Mock())

    assert result_set.DataFrame().equals(pd.DataFrame({"x": range(3)}))


def test_resultset_polars_dataframe(result_set, monkeypatch):
    assert result_set.PolarsDataFrame().frame_equal(pl.DataFrame({"x": range(3)}))


def test_resultset_csv(result_set, tmp_empty):
    result_set.csv("file.csv")

    assert Path("file.csv").read_text() == "x\n0\n1\n2\n"


def test_resultset_str(result_set):
    assert str(result_set) == "+---+\n| x |\n+---+\n| 0 |\n| 1 |\n| 2 |\n+---+"


def test_resultset_repr_html(result_set):
    html_ = result_set._repr_html_()
    assert (
        "<span style='font-style:italic;font-size:11px'>"
        "<code>ResultSet</code> : to convert to pandas, call <a href="
        "'https://jupysql.ploomber.io/en/latest/integrations/pandas.html'>"
        "<code>.DataFrame()</code></a> or to polars, call <a href="
        "'https://jupysql.ploomber.io/en/latest/integrations/polars.html'>"
        "<code>.PolarsDataFrame()</code></a></span><br>"
    ) in html_

    assert "Truncated to displaylimit of 5" in html_


@pytest.mark.parametrize(
    "fname, parameters",
    [
        ("head", -1),
        ("tail", None),
        ("value_counts", None),
        ("not_df_function", None),
    ],
)
def test_invalid_operation_error(result_set, fname, parameters):
    with pytest.raises(AttributeError) as excinfo:
        getattr(result_set, fname)(parameters)

    assert str(excinfo.value) == (
        f"'{fname}' is not a valid operation, you can convert this "
        "into a pandas data frame by calling '.DataFrame()' or a "
        "polars data frame by calling '.PolarsDataFrame()'"
    )


def test_resultset_config_autolimit_dict(result, config):
    config.autolimit = 1
    resultset = ResultSet(result, config, statement=None, conn=Mock())
    assert resultset.dict() == {"x": (0,)}


# TODO: add dbapi tests


@pytest.fixture
def results(ip_empty):
    engine = create_engine("duckdb://")
    session = engine.connect()

    session.execute(text("CREATE TABLE a (x INT,);"))

    session.execute(text("INSERT INTO a(x) VALUES (1),(2),(3),(4),(5);"))

    sql = "SELECT * FROM a"
    results = session.execute(text(sql))

    results.fetchmany = Mock(wraps=results.fetchmany)
    results.fetchall = Mock(wraps=results.fetchall)
    results.fetchone = Mock(wraps=results.fetchone)

    yield results

    session.close()


@pytest.mark.parametrize("uri", ["duckdb://", "sqlite://"])
def test_convert_to_dataframe(ip_empty, uri):
    engine = create_engine(uri)
    session = engine.connect()

    mock = Mock()
    mock.displaylimit = 100
    mock.autolimit = 100000

    results = session.execute(text("CREATE TABLE a (x INT);"))

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    df = rs.DataFrame()

    assert df.to_dict() == {}


def test_convert_to_dataframe_2(ip_empty):
    engine = create_engine("duckdb://")
    session = engine.connect()

    mock = Mock()
    mock.displaylimit = 100
    mock.autolimit = 100000

    session.execute(text("CREATE TABLE a (x INT,);"))
    results = session.execute(text("INSERT INTO a(x) VALUES (1),(2),(3),(4),(5);"))
    rs = ResultSet(results, mock, statement=None, conn=Mock())
    df = rs.DataFrame()

    assert df.to_dict() == {"Count": {0: 5}}


@pytest.mark.parametrize("uri", ["duckdb://", "sqlite://"])
def test_convert_to_dataframe_3(ip_empty, uri):
    engine = create_engine(uri)
    session = engine.connect()

    mock = Mock()
    mock.displaylimit = 100
    mock.autolimit = 100000

    session.execute(text("CREATE TABLE a (x INT);"))
    session.execute(text("INSERT INTO a(x) VALUES (1),(2),(3),(4),(5);"))
    results = session.execute(text("SELECT * FROM a"))

    rs = ResultSet(results, mock, statement="SELECT * FROM a", conn=Mock())
    df = rs.DataFrame()

    # TODO: check native duckdb was called if using duckb
    assert df.to_dict() == {"x": {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}}


def test_done_fetching_if_reached_autolimit(results):
    mock = Mock()
    mock.autolimit = 2
    mock.displaylimit = 100

    rs = ResultSet(results, mock, statement=None, conn=Mock())

    assert rs.did_finish_fetching() is True


def test_done_fetching_if_reached_autolimit_2(results):
    mock = Mock()
    mock.autolimit = 4
    mock.displaylimit = 100

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    list(rs)

    assert rs.did_finish_fetching() is True


@pytest.mark.parametrize("method", ["__repr__", "_repr_html_"])
@pytest.mark.parametrize("autolimit", [1000_000, 0])
def test_no_displaylimit(results, method, autolimit):
    mock = Mock()
    mock.displaylimit = 0
    mock.autolimit = autolimit

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    getattr(rs, method)()

    assert rs._results == [(1,), (2,), (3,), (4,), (5,)]
    assert rs.did_finish_fetching() is True


def test_no_fetching_if_one_result():
    engine = create_engine("duckdb://")
    session = engine.connect()

    session.execute(text("CREATE TABLE a (x INT,);"))
    session.execute(text("INSERT INTO a(x) VALUES (1);"))

    mock = Mock()
    mock.displaylimit = 100
    mock.autolimit = 1000_000

    results = session.execute(text("SELECT * FROM a"))
    results.fetchmany = Mock(wraps=results.fetchmany)
    results.fetchall = Mock(wraps=results.fetchall)
    results.fetchone = Mock(wraps=results.fetchone)

    rs = ResultSet(results, mock, statement=None, conn=Mock())

    assert rs.did_finish_fetching() is True
    results.fetchall.assert_not_called()
    results.fetchmany.assert_called_once_with(size=2)
    results.fetchone.assert_not_called()

    str(rs)
    list(rs)

    results.fetchall.assert_not_called()
    results.fetchmany.assert_called_once_with(size=2)
    results.fetchone.assert_not_called()


# TODO: try with other values, and also change the display limit and re-run the repr
# TODO: try with __repr__ and __str__
def test_resultset_fetches_required_rows(results):
    mock = Mock()
    mock.displaylimit = 3
    mock.autolimit = 1000_000

    ResultSet(results, mock, statement=None, conn=Mock())
    # rs.fetch_results()
    # rs._repr_html_()
    # str(rs)

    results.fetchall.assert_not_called()
    results.fetchmany.assert_called_once_with(size=2)
    results.fetchone.assert_not_called()


def test_fetches_remaining_rows(results):
    mock = Mock()
    mock.displaylimit = 1
    mock.autolimit = 1000_000

    rs = ResultSet(results, mock, statement=None, conn=Mock())

    # this will trigger fetching two
    str(rs)

    results.fetchall.assert_not_called()
    results.fetchmany.assert_has_calls([call(size=2)])
    results.fetchone.assert_not_called()

    # this will trigger fetching the rest
    assert list(rs) == [(1,), (2,), (3,), (4,), (5,)]

    results.fetchall.assert_called_once_with()
    results.fetchmany.assert_has_calls([call(size=2)])
    results.fetchone.assert_not_called()

    rs.sqlaproxy.fetchmany = Mock(side_effect=ValueError("fetchmany called"))
    rs.sqlaproxy.fetchall = Mock(side_effect=ValueError("fetchall called"))
    rs.sqlaproxy.fetchone = Mock(side_effect=ValueError("fetchone called"))

    # this should not trigger any more fetching
    assert list(rs) == [(1,), (2,), (3,), (4,), (5,)]


@pytest.mark.parametrize(
    "method, repr_expected",
    [
        [
            "__repr__",
            "+---+\n| x |\n+---+\n| 1 |\n| 2 |\n| 3 |\n+---+",
        ],
        [
            "_repr_html_",
            "<table>\n    <thead>\n        <tr>\n            <th>x</th>\n        "
            "</tr>\n    </thead>\n    <tbody>\n        <tr>\n            "
            "<td>1</td>\n        </tr>\n        <tr>\n            "
            "<td>2</td>\n        </tr>\n        <tr>\n            "
            "<td>3</td>\n        </tr>\n    </tbody>\n</table>",
        ],
    ],
    ids=["repr", "repr_html"],
)
def test_resultset_fetches_required_rows_repr(results, method, repr_expected):
    mock = Mock()
    mock.displaylimit = 3
    mock.autolimit = 1000_000

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    repr_returned = getattr(rs, method)()

    assert repr_expected in repr_returned
    assert rs.did_finish_fetching() is False
    results.fetchall.assert_not_called()
    results.fetchmany.assert_has_calls([call(size=2), call(size=1)])
    results.fetchone.assert_not_called()


def test_resultset_fetches_no_rows(results):
    mock = Mock()
    mock.displaylimit = 1
    mock.autolimit = 1000_000

    ResultSet(results, mock, statement=None, conn=Mock())

    results.fetchmany.assert_has_calls([call(size=2)])
    results.fetchone.assert_not_called()
    results.fetchall.assert_not_called()


def test_resultset_autolimit_one(results):
    mock = Mock()
    mock.displaylimit = 10
    mock.autolimit = 1

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    repr(rs)
    str(rs)
    rs._repr_html_()
    list(rs)

    results.fetchmany.assert_has_calls([call(size=1)])
    results.fetchone.assert_not_called()
    results.fetchall.assert_not_called()


def test_display_limit_respected_even_when_feched_all(results):
    mock = Mock()
    mock.displaylimit = 2
    mock.autolimit = 0

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    elements = list(rs)

    assert len(elements) == 5
    assert str(rs) == "+---+\n| x |\n+---+\n| 1 |\n| 2 |\n+---+"
    assert (
        "<table>\n    <thead>\n        <tr>\n            <th>x</th>\n        "
        "</tr>\n    </thead>\n    <tbody>\n        <tr>\n            "
        "<td>1</td>\n        </tr>\n        <tr>\n            <td>2</td>\n"
        "        </tr>\n    </tbody>\n</table>" in rs._repr_html_()
    )


# TODO: try with more values of displaylimit
# TODO: test some edge cases. e.g., displaylimit is set to 10 but we only have 5 rows
def test_displaylimit_message(results):
    mock = Mock()
    mock.displaylimit = 1
    mock.autolimit = 0

    rs = ResultSet(results, mock, statement=None, conn=Mock())

    assert "Truncated to displaylimit of 1" in rs._repr_html_()


def test_refreshes_sqlaproxy_for_sqlalchemy_duckdb():
    pass


def test_doesnt_refresh_sqlaproxy_for_if_not_sqlalchemy_and_duckdb():
    pass


def test_doesnt_refresh_sqlaproxy_if_different_connection():
    pass
