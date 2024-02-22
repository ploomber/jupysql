import string
from unittest.mock import Mock, call

import duckdb
from sqlalchemy import create_engine, text
from pathlib import Path


import pytest
import pandas as pd
import polars as pl
import sqlalchemy

from sql.connection import DBAPIConnection, SQLAlchemyConnection
from sql.run.resultset import ResultSet
from sql.connection.connection import IS_SQLALCHEMY_ONE

import warnings


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

    conn = SQLAlchemyConnection(engine)
    result = conn.raw_execute("select * from df")

    yield result, conn
    conn.close()


@pytest.fixture
def result_set(result, config):
    result_set, conn = result
    return ResultSet(result_set, config, statement="select * from df", conn=conn)


def test_resultset_getitem(result_set):
    assert result_set[0] == (0,)
    assert result_set[0:2] == [(0,), (1,)]


def test_resultset_dict(result_set):
    assert result_set.dict() == {"x": (0, 1, 2)}


def test_resultset_len(result_set):
    assert len(result_set) == 3


def test_resultset_dicts(result_set):
    assert list(result_set.dicts()) == [{"x": 0}, {"x": 1}, {"x": 2}]


def test_resultset_dataframe(result_set, config):
    # since this will use the native method, the issue will be re-executed
    # so we need to create the df here so duckdb can find it
    df = pd.DataFrame({"x": range(3)})  # noqa
    assert result_set.DataFrame().equals(pd.DataFrame({"x": range(3)}))


def test_resultset_polars_dataframe(result_set):
    # since this will use the native method, the issue will be re-executed
    # so we need to create the df here so duckdb can find it
    df = pd.DataFrame({"x": range(3)})  # noqa
    assert result_set.PolarsDataFrame().frame_equal(pl.DataFrame({"x": range(3)}))


def test_resultset_csv(result_set, tmp_empty):
    result_set.csv("file.csv")

    assert Path("file.csv").read_text() == "x\n0\n1\n2\n"


def test_resultset_str(result_set):
    assert str(result_set) == "+---+\n| x |\n+---+\n| 0 |\n| 1 |\n| 2 |\n+---+"


def test_resultset_repr_html_when_feedback_is_2(result_set, ip_empty):
    ip_empty.run_cell("%config SqlMagic.feedback = 2")

    html_ = result_set._repr_html_()
    assert (
        "<span style='font-style:italic;font-size:11px'>"
        "<code>ResultSet</code>: to convert to pandas, call <a href="
        "'https://jupysql.ploomber.io/en/latest/integrations/pandas.html'>"
        "<code>.DataFrame()</code></a> or to polars, call <a href="
        "'https://jupysql.ploomber.io/en/latest/integrations/polars.html'>"
        "<code>.PolarsDataFrame()</code></a></span><br>"
    ) in html_

    plain = (
        "ResultSet: to convert to pandas, call .DataFrame() "
        "or to polars, call .PolarsDataFrame()"
    )
    assert plain in str(result_set)
    assert plain in repr(result_set)


@pytest.mark.parametrize("feedback", [0, 1])
def test_resultset_repr_html_with_reduced_feedback(result_set, ip_empty, feedback):
    ip_empty.run_cell(f"%config SqlMagic.feedback = {feedback}")

    html = result_set._repr_html_()
    assert "pandas" not in html
    assert "polars" not in html


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
    resultset = ResultSet(result[0], config, statement=None, conn=result[1])

    assert resultset.dict() == {"x": (0,)}


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


@pytest.fixture
def duckdb_sqlalchemy(ip_empty):
    conn = SQLAlchemyConnection(create_engine("duckdb://"))
    yield conn


@pytest.fixture
def sqlite_sqlalchemy(ip_empty):
    conn = SQLAlchemyConnection(create_engine("sqlite://"))
    yield conn


@pytest.fixture
def duckdb_dbapi():
    conn_ = duckdb.connect(":memory:")
    conn = DBAPIConnection(conn_)
    yield conn


@pytest.fixture
def mock_config():
    mock = Mock()
    mock.displaylimit = 100
    mock.autolimit = 100000
    yield mock


@pytest.mark.parametrize(
    "session, expected_value",
    [
        ("duckdb_sqlalchemy", {"Count": {}} if IS_SQLALCHEMY_ONE else {"Success": {}}),
        ("duckdb_dbapi", {"Count": {}}),
        ("sqlite_sqlalchemy", {}),
    ],
)
def test_convert_to_dataframe_create_table(
    session, expected_value, request, mock_config
):
    session = request.getfixturevalue(session)

    statement = "CREATE TABLE a (x INT);"
    results = session.execute(statement)

    rs = ResultSet(results, mock_config, statement=statement, conn=session)
    df = rs.DataFrame()

    assert df.to_dict() == expected_value


@pytest.mark.parametrize(
    "session, expected_value",
    [
        pytest.param(
            "duckdb_sqlalchemy",
            {"Count": {0: 5}},
            marks=pytest.mark.xfail(
                reason="inconsistent behavior between sqlalchemy 1.x and 2.x"
            ),
        ),
        ("duckdb_dbapi", {"Count": {0: 5}}),
        ("sqlite_sqlalchemy", {}),
    ],
    ids=[
        "duckdb_sqlalchemy",
        "duckdb_dbapi",
        "sqlite_sqlalchemy",
    ],
)
def test_convert_to_dataframe_insert_into(
    session, expected_value, request, mock_config
):
    session = request.getfixturevalue(session)

    session.execute("CREATE TABLE a (x INT,);")
    statement = "INSERT INTO a(x) VALUES (1),(2),(3),(4),(5);"
    results = session.execute(statement)
    rs = ResultSet(results, mock_config, statement=statement, conn=session)
    df = rs.DataFrame()

    assert df.to_dict() == expected_value


@pytest.mark.parametrize(
    "session",
    [
        "duckdb_sqlalchemy",
        "duckdb_dbapi",
        "sqlite_sqlalchemy",
    ],
)
@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM a",
        "with something as (SELECT * FROM a) select * from something",
    ],
)
def test_convert_to_dataframe_select(session, request, mock_config, statement):
    session = request.getfixturevalue(session)

    session.execute("CREATE TABLE a (x INT);")
    session.execute("INSERT INTO a(x) VALUES (1),(2),(3),(4),(5);")
    results = session.execute(statement)

    rs = ResultSet(results, mock_config, statement=statement, conn=session)
    df = rs.DataFrame()

    assert df.to_dict() == {"x": {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}}


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM a",
        "\nSELECT * FROM a",
        "    SELECT * FROM a",
        "FROM a",
        "\nFROM a",
        "    FROM a",
    ],
    ids=[
        "select",
        "select-with-newline",
        "select-with-spaces",
        "from",
        "from-with-newline",
        "from-with-spaces",
    ],
)
@pytest.mark.parametrize(
    "to_df_method, expected_value",
    [
        ("DataFrame", {"x": {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}}),
        ("PolarsDataFrame", {"x": [1, 2, 3, 4, 5]}),
    ],
)
def test_convert_to_dataframe_using_native_duckdb(
    ip_empty, query, to_df_method, expected_value, mock_config
):
    session = duckdb.connect()

    session.execute("CREATE TABLE a (x INT);")
    session.execute("INSERT INTO a(x) VALUES (1),(2),(3),(4),(5);")
    results = session.execute(query)

    rs = ResultSet(results, mock_config, statement=query, conn=DBAPIConnection(session))
    # force fetching
    list(rs)

    df = getattr(rs, to_df_method)()

    d = df.to_dict()

    if to_df_method == "PolarsDataFrame":
        d["x"] = list(d["x"])

    assert d == expected_value


def test_done_fetching_if_reached_autolimit(results):
    mock = Mock()
    mock.autolimit = 2
    mock.displaylimit = 100

    rs = ResultSet(results, mock, statement=None, conn=Mock())

    assert rs._done_fetching() is True


def test_done_fetching_if_reached_autolimit_2(results):
    mock = Mock()
    mock.autolimit = 4
    mock.displaylimit = 100

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    # force fetching from db
    list(rs)

    assert rs._done_fetching() is True


@pytest.mark.parametrize("method", ["__repr__", "_repr_html_"])
@pytest.mark.parametrize("autolimit", [1000_000, 0])
def test_no_displaylimit(results, method, autolimit):
    mock = Mock()
    mock.displaylimit = 0
    mock.autolimit = autolimit

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    getattr(rs, method)()

    assert rs._results == [(1,), (2,), (3,), (4,), (5,)]
    assert rs._done_fetching() is True


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

    assert rs._done_fetching() is True
    results.fetchall.assert_not_called()
    results.fetchmany.assert_called_once_with(size=2)
    results.fetchone.assert_not_called()

    str(rs)
    list(rs)

    results.fetchall.assert_not_called()
    results.fetchmany.assert_called_once_with(size=2)
    results.fetchone.assert_not_called()


def test_resultset_fetches_minimum_number_of_rows(results):
    mock = Mock()
    mock.displaylimit = 3
    mock.autolimit = 1000_000

    ResultSet(results, mock, statement=None, conn=Mock())

    results.fetchall.assert_not_called()
    results.fetchmany.assert_called_once_with(size=2)
    results.fetchone.assert_not_called()


@pytest.mark.parametrize("method", ["__repr__", "_repr_html_"])
def test_resultset_fetches_minimum_number_of_rows_for_repr(results, method):
    mock = Mock()
    mock.displaylimit = 3
    mock.autolimit = 1000_000

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    getattr(rs, method)()

    results.fetchall.assert_not_called()
    assert results.fetchmany.call_args_list == [call(size=2), call(size=1)]
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
    ids=[
        "repr",
        "repr_html",
    ],
)
def test_resultset_fetches_required_rows_repr(results, method, repr_expected):
    mock = Mock()
    mock.displaylimit = 3
    mock.autolimit = 1000_000

    rs = ResultSet(results, mock, statement=None, conn=Mock())
    repr_returned = getattr(rs, method)()

    assert repr_expected in repr_returned
    assert rs._done_fetching() is False
    results.fetchall.assert_not_called()
    results.fetchmany.assert_has_calls([call(size=2), call(size=1)])
    results.fetchone.assert_not_called()


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


@pytest.mark.parametrize(
    "displaylimit, message",
    [
        (1, "Truncated to $DISPLAYLIMIT of 1."),
        (2, "Truncated to $DISPLAYLIMIT of 2."),
    ],
)
def test_displaylimit_truncated_footer(displaylimit, message, results):
    HTML_LINK = (
        '<a href="https://jupysql.ploomber.io/en/'
        'latest/api/configuration.html#displaylimit">displaylimit</a>'
    )

    mock = Mock()
    mock.displaylimit = displaylimit
    mock.autolimit = 0

    rs = ResultSet(results, mock, statement=None, conn=Mock())

    message_html = string.Template(message).substitute(DISPLAYLIMIT=HTML_LINK)
    assert message_html in rs._repr_html_()

    message_plain = string.Template(message).substitute(DISPLAYLIMIT="displaylimit")
    assert message_plain in repr(rs)
    assert message_plain in str(rs)


@pytest.mark.parametrize("displaylimit", [0, 1000])
def test_no_displaylimit_message(results, displaylimit):
    mock = Mock()
    mock.displaylimit = displaylimit
    mock.autolimit = 0

    rs = ResultSet(results, mock, statement=None, conn=Mock())

    assert "Truncated to displaylimit" not in rs._repr_html_()
    assert "Truncated to displaylimit" not in repr(rs)
    assert "Truncated to displaylimit" not in str(rs)


def test_refreshes_sqlaproxy_for_sqlalchemy_duckdb():
    first = SQLAlchemyConnection(create_engine("duckdb://"))
    first.execute("CREATE TABLE numbers (x INTEGER)")
    first.execute("INSERT INTO numbers VALUES (1), (2), (3), (4), (5)")
    first.execute("CREATE TABLE characters (c VARCHAR)")
    first.execute("INSERT INTO characters VALUES ('a'), ('b'), ('c'), ('d'), ('e')")

    mock = Mock()
    mock.displaylimit = 10
    mock.autolimit = 0

    statement = "SELECT * FROM numbers"
    first_set = ResultSet(
        first.raw_execute(statement), mock, statement=statement, conn=first
    )

    original_id = id(first_set._sqlaproxy)

    # create a new resultset so the other one is no longer the latest one
    statement = "SELECT * FROM characters"
    ResultSet(first.raw_execute(statement), mock, statement=statement, conn=first)

    # force fetching data, this should trigger a refresh
    list(first_set)

    assert id(first_set._sqlaproxy) != original_id


def test_doesnt_refresh_sqlaproxy_for_if_not_sqlalchemy_and_duckdb():
    first = DBAPIConnection(duckdb.connect(":memory:"))
    first.execute("CREATE TABLE numbers (x INTEGER)")
    first.execute("INSERT INTO numbers VALUES (1), (2), (3), (4), (5)")
    first.execute("CREATE TABLE characters (c VARCHAR)")
    first.execute("INSERT INTO characters VALUES ('a'), ('b'), ('c'), ('d'), ('e')")

    mock = Mock()
    mock.displaylimit = 10
    mock.autolimit = 0

    statement = "SELECT * FROM numbers"
    first_set = ResultSet(
        first.raw_execute(statement), mock, statement=statement, conn=first
    )

    original_id = id(first_set._sqlaproxy)

    # create a new resultset so the other one is no longer the latest one
    statement = "SELECT * FROM characters"
    ResultSet(first.raw_execute(statement), mock, statement=statement, conn=first)

    # force fetching data, this should not trigger a refresh
    list(first_set)

    assert id(first_set._sqlaproxy) == original_id


def test_doesnt_refresh_sqlaproxy_if_different_connection():
    first = SQLAlchemyConnection(create_engine("duckdb://"))
    first.execute("CREATE TABLE numbers (x INTEGER)")
    first.execute("INSERT INTO numbers VALUES (1), (2), (3), (4), (5)")

    second = SQLAlchemyConnection(create_engine("duckdb://"))
    second.execute("CREATE TABLE characters (c VARCHAR)")
    second.execute("INSERT INTO characters VALUES ('a'), ('b'), ('c'), ('d'), ('e')")

    mock = Mock()
    mock.displaylimit = 10
    mock.autolimit = 0

    statement = "SELECT * FROM numbers"
    first_set = ResultSet(
        first.raw_execute(statement), mock, statement=statement, conn=first
    )

    original_id = id(first_set._sqlaproxy)

    statement = "SELECT * FROM characters"
    ResultSet(second.raw_execute(statement), mock, statement=statement, conn=second)

    # force fetching data
    list(first_set)

    assert id(first_set._sqlaproxy) == original_id


@pytest.mark.parametrize(
    "function, expected_warning, dataset",
    [
        (
            "pie",
            (
                ".pie() is deprecated and will be removed in a future version. "
                "Use %sqlplot pie instead. "
                "For more help, find us at https://ploomber.io/community "
            ),
            {
                "x": [1, 2, 3],
                "y": [4, 5, 6],
            },
        ),
        (
            "bar",
            (
                ".bar() is deprecated and will be removed in a future version. "
                "Use %sqlplot bar instead. "
                "For more help, find us at https://ploomber.io/community "
            ),
            {
                "x": [1, 2, 3],
            },
        ),
        (
            "plot",
            (
                ".plot() is deprecated and will be removed in a future version. "
                "For more help, find us at https://ploomber.io/community "
            ),
            {
                "x": [1, 2, 3],
            },
        ),
    ],
)
def test_calling_legacy_plotting_functions_displays_warning(
    config, function, expected_warning, dataset
):
    df = pd.DataFrame(dataset)  # noqa
    engine = sqlalchemy.create_engine("duckdb://")
    conn = SQLAlchemyConnection(engine)
    result = conn.raw_execute("select * from df")

    rs = ResultSet(result, config, statement="select * from df", conn=conn)

    with warnings.catch_warnings(record=True) as record:
        getattr(rs, function)()

    assert len(record) == 1
    assert str(record[0].message) == expected_warning


@pytest.mark.xfail(reason="Failing intermittently with DuckDB v0.10.0")
@pytest.mark.parametrize(
    "df_type, library, equal_func",
    [
        (
            "autopandas",
            pd,
            "equals",
        ),
        (
            "autopolars",
            pl,
            "frame_equal",
        ),
    ],
)
def test_pivot_dataframe_conversion_results(ip, df_type, library, equal_func):
    # Setup connection, data
    ip.run_cell(
        """import duckdb
conn = duckdb.connect()"""
    )
    ip.run_cell("%sql conn --alias duckdb-mem")
    ip.run_cell(
        """
    %%sql
CREATE OR REPLACE TABLE Cities(Country VARCHAR, Name VARCHAR, Year INT, Population INT);
INSERT INTO Cities VALUES ('NL', 'Amsterdam', 2000, 1005);
INSERT INTO Cities VALUES ('NL', 'Amsterdam', 2010, 1065);
INSERT INTO Cities VALUES ('NL', 'Amsterdam', 2020, 1158);
INSERT INTO Cities VALUES ('US', 'Seattle', 2000, 564);
INSERT INTO Cities VALUES ('US', 'Seattle', 2010, 608);
INSERT INTO Cities VALUES ('US', 'Seattle', 2020, 738);
INSERT INTO Cities VALUES ('US', 'New York City', 2000, 8015);
INSERT INTO Cities VALUES ('US', 'New York City', 2010, 8175);
INSERT INTO Cities VALUES ('US', 'New York City', 2020, 8772);
    """
    )

    # Run Pivot statement as baseline
    expected = ip.run_cell(
        """%%sql
    PIVOT Cities ON Year USING SUM(Population)"""
    ).result

    # Turn on auto-convert (also do with autopolars)
    ip.run_cell(f"%config SqlMagic.{df_type} = True")

    # Run Pivot statement again and ensure equal
    result = ip.run_cell(
        """%%sql
    PIVOT Cities ON Year USING SUM(Population)"""
    ).result

    # Assert result matches expected
    expected_result = {
        "Country": ["US", "US", "NL"],
        "Name": ["New York City", "Seattle", "Amsterdam"],
        "2000": [8015.0, 564.0, 1005.0],
        "2010": [8175.0, 608.0, 1065.0],
        "2020": [8772.0, 738.0, 1158.0],
    }
    expected = getattr(library, "DataFrame")(expected_result)
    assert getattr(result, equal_func)(expected)
