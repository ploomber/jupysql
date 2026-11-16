import pytest

from sql.connection import ADBCConnection, ConnectionManager, is_adbc
from sql.run.arrowcursor import ArrowCursor

adbc_sqlite = pytest.importorskip("adbc_driver_sqlite.dbapi")
pa = pytest.importorskip("pyarrow")
pl = pytest.importorskip("polars")


@pytest.fixture
def ip_adbc(ip_empty):
    ip_empty.run_cell(
        "import adbc_driver_sqlite.dbapi; conn = adbc_driver_sqlite.dbapi.connect()"
    )
    ip_empty.run_cell("%sql conn")
    ip_empty.run_cell("""%%sql
CREATE TABLE numbers (n INTEGER, name TEXT, x REAL);
INSERT INTO numbers
WITH RECURSIVE s(v) AS (SELECT 1 UNION ALL SELECT v + 1 FROM s WHERE v < 5000)
SELECT v, 'name-' || v, v * 0.5 FROM s;
""")
    yield ip_empty
    ConnectionManager.close_all()


def test_is_adbc():
    conn = adbc_sqlite.connect()
    assert is_adbc(conn)
    conn.close()


def test_is_adbc_rejects_sqlite3():
    import sqlite3

    assert not is_adbc(sqlite3.connect(":memory:"))


def test_adbc_connection_metadata(ip_adbc):
    conn = ConnectionManager.current
    assert isinstance(conn, ADBCConnection)
    assert conn.alias == "adbc-sqlite"
    assert conn.dialect == "sqlite"
    assert conn._get_database_information()["driver"] == "ADBC SQLite Driver"


def test_adbc_resultset_uses_arrow_cursor(ip_adbc):
    rs = ip_adbc.run_cell("%sql SELECT * FROM numbers ORDER BY n").result
    assert isinstance(rs.sqlaproxy, ArrowCursor)
    assert rs._results[:2] == [(1, "name-1", 0.5), (2, "name-2", 1.0)]
    assert len(rs) == 5000
    assert list(rs)[-1] == (5000, "name-5000", 2500.0)


def test_adbc_arrow_table_includes_fetched_rows(ip_adbc):
    rs = ip_adbc.run_cell("%sql SELECT * FROM numbers ORDER BY n").result
    rs.fetchmany(10)
    table = rs.ArrowTable()
    assert isinstance(table, pa.Table)
    assert table.num_rows == 5000
    assert table.column("n").to_pylist()[:3] == [1, 2, 3]


def test_adbc_polars_dataframe(ip_adbc):
    rs = ip_adbc.run_cell("%sql SELECT * FROM numbers ORDER BY n").result
    df = rs.PolarsDataFrame()
    assert df.shape == (5000, 3)
    assert df.columns == ["n", "name", "x"]
    utf = getattr(pl, "String", pl.Utf8)
    assert df.dtypes == [pl.Int64, utf, pl.Float64]
    assert df.row(4999) == (5000, "name-5000", 2500.0)


def test_adbc_autopolars(ip_adbc):
    ip_adbc.run_cell("%config SqlMagic.autopolars = True")
    df = ip_adbc.run_cell("%sql SELECT n FROM numbers WHERE n <= 3 ORDER BY n").result
    assert isinstance(df, pl.DataFrame)
    assert df["n"].to_list() == [1, 2, 3]


def test_adbc_display_respects_displaylimit(ip_adbc):
    ip_adbc.run_cell("%config SqlMagic.displaylimit = 3")
    rs = ip_adbc.run_cell("%sql SELECT n FROM numbers ORDER BY n").result
    html = rs._repr_html_()
    assert "Truncated to" in html
    assert rs.sqlaproxy._offset == 3


def test_adbc_statement_without_results(ip_adbc):
    rs = ip_adbc.run_cell("%sql CREATE TABLE other (a INTEGER)").result
    assert rs.keys == []
    assert list(rs) == []


def test_adbc_query_after_ddl(ip_adbc):
    ip_adbc.run_cell("%sql INSERT INTO numbers VALUES (6000, 'x', 1.0)")
    rs = ip_adbc.run_cell("%sql SELECT COUNT(*) AS c FROM numbers").result
    assert list(rs) == [(5001,)]


def test_arrow_cursor_fetch_methods():
    conn = adbc_sqlite.connect()
    cur = conn.cursor()
    cur.execute(
        "WITH RECURSIVE s(v) AS (SELECT 1 UNION ALL SELECT v + 1 FROM s WHERE v < 10)"
        " SELECT v FROM s"
    )
    arrow_cursor = ArrowCursor(cur)
    assert arrow_cursor.fetchone() == (1,)
    assert arrow_cursor.fetchmany(3) == [(2,), (3,), (4,)]
    assert arrow_cursor.fetchall() == [(i,) for i in range(5, 11)]
    assert arrow_cursor.fetchall() == []
    assert arrow_cursor.fetch_arrow_table().num_rows == 10
    arrow_cursor.close()
    conn.close()


def test_resultset_arrow_table_non_adbc(ip_dbapi):
    table = ip_dbapi.run_cell("%sql SELECT * FROM test").result.ArrowTable()
    assert table.to_pydict() == {"n": [1, 2], "name": ["foo", "bar"]}
