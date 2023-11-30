import os
import urllib.request
from pathlib import Path

import pytest

from sql.magic import SqlMagic, RenderMagic
from sql.magic_plot import SqlPlotMagic
from sql.magic_cmd import SqlCmdMagic
from sql.connection import ConnectionManager
from sql._testing import TestingShell
from sql import connection
from sql.store import store
from sql import _current

PATH_TO_TESTS = Path(__file__).absolute().parent
PATH_TO_TMP_ASSETS = PATH_TO_TESTS / "tmp"
PATH_TO_TMP_ASSETS.mkdir(exist_ok=True)


@pytest.fixture
def check_duplicate_message_factory():
    def _generate_error_message(cmd, args, aliases=None):
        error_message = ""
        duplicates = set([arg for arg in args if args.count(arg) != 1])

        if duplicates:
            error_message += (
                f"Duplicate arguments in %{cmd}. "
                "Please use only one of each of the following: "
                f"{', '.join(sorted(duplicates))}."
            )
            if aliases:
                error_message += " "

        if aliases:
            alias_list = []
            for pair in sorted(aliases):
                print(pair[0], pair[1])
                alias_list.append(f"{f'-{pair[0]}'} or {f'--{pair[1]}'}")
            error_message += (
                f"Duplicate aliases for arguments in %{cmd}. "
                "Please use either one of "
                f"{', '.join(alias_list)}."
            )

        return error_message

    return _generate_error_message


@pytest.fixture(scope="function", autouse=True)
def isolate_tests(monkeypatch):
    """
    Fixture to ensure connections are isolated between tests, preventing tests
    from accidentally closing connections created by other tests.

    Also clear up any stored snippets.
    """
    # reset connections
    connections = {}
    monkeypatch.setattr(connection.ConnectionManager, "connections", connections)
    monkeypatch.setattr(connection.ConnectionManager, "current", None)

    # reset store
    store.clear()

    yield

    # close connections
    connection.ConnectionManager.close_all()


def path_to_tests():
    return PATH_TO_TESTS


@pytest.fixture
def chinook_db():
    path = PATH_TO_TMP_ASSETS / "my.db"
    if not path.is_file():
        url = (
            "https://raw.githubusercontent.com"
            "/lerocha/chinook-database/master/"
            "ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
        )
        urllib.request.urlretrieve(url, path)

    return str(path)


# TODO: this is legacy code, we need to remove it
def runsql(ip_session, statements):
    if isinstance(statements, str):
        statements = [statements]
    for statement in statements:
        result = ip_session.run_line_magic("sql", "sqlite:// %s" % statement)
    return result  # returns only last result


@pytest.fixture
def clean_conns():
    ConnectionManager.current = None
    ConnectionManager.connections = dict()
    yield


@pytest.fixture
def ip_no_magics():
    ip_session = TestingShell.preconfigured_shell()

    # to prevent using the actual default, which reads from the home directory
    ip_session.run_cell("%config SqlMagic.dsn_filename = 'default.ini'")

    yield ip_session
    ConnectionManager.close_all()


@pytest.fixture
def ip_empty(ip_no_magics):
    sql_magic = SqlMagic(ip_no_magics)
    _current._set_sql_magic(sql_magic)

    ip_no_magics.register_magics(sql_magic)
    ip_no_magics.register_magics(RenderMagic)
    ip_no_magics.register_magics(SqlPlotMagic)
    ip_no_magics.register_magics(SqlCmdMagic)

    yield ip_no_magics
    ConnectionManager.close_all()


@pytest.fixture
def sql_magic():
    ip_session = TestingShell.preconfigured_shell()

    sql_magic = SqlMagic(ip_session)

    yield sql_magic
    ConnectionManager.close_all()


def insert_sample_data(ip):
    ip.run_cell(
        """%%sql
CREATE TABLE test (n INT, name TEXT);
INSERT INTO test VALUES (1, 'foo');
INSERT INTO test VALUES (2, 'bar');
CREATE TABLE [table with spaces] (first INT, second TEXT);
CREATE TABLE author (first_name, last_name, year_of_death);
INSERT INTO author VALUES ('William', 'Shakespeare', 1616);
INSERT INTO author VALUES ('Bertold', 'Brecht', 1956);
CREATE TABLE empty_table (column INT, another INT);
CREATE TABLE website (person, link, birthyear INT);
INSERT INTO website VALUES ('Bertold Brecht',
    'https://en.wikipedia.org/wiki/Bertolt_Brecht', 1954 );
INSERT INTO website VALUES ('William Shakespeare',
    'https://en.wikipedia.org/wiki/William_Shakespeare', 1564);
INSERT INTO website VALUES ('Steve Steve', 'google_link', 2023);
CREATE TABLE number_table (x INT, y INT);
INSERT INTO number_table VALUES (4, (-2));
INSERT INTO number_table VALUES ((-5), 0);
INSERT INTO number_table VALUES (2, 4);
INSERT INTO number_table VALUES (0, 2);
INSERT INTO number_table VALUES ((-5), (-1));
INSERT INTO number_table VALUES ((-2), (-3));
INSERT INTO number_table VALUES ((-2), (-3));
INSERT INTO number_table VALUES ((-4), 2);
INSERT INTO number_table VALUES (2, (-5));
INSERT INTO number_table VALUES (4, 3);
"""
    )


@pytest.fixture
def ip(ip_empty):
    """Provides an IPython session in which tables have been created"""
    ip_empty.run_cell("%sql sqlite://")
    insert_sample_data(ip_empty)

    yield ip_empty

    ConnectionManager.close_all()


@pytest.fixture
def ip_dbapi(ip_empty):
    ip_empty.run_cell("import sqlite3; conn = sqlite3.connect(':memory:');")
    ip_empty.run_cell("%sql conn")
    insert_sample_data(ip_empty)

    yield ip_empty

    ConnectionManager.close_all()


@pytest.fixture
def tmp_empty(tmp_path):
    """
    Create temporary path using pytest native fixture,
    them move it, yield, and restore the original path
    """

    old = os.getcwd()
    os.chdir(str(tmp_path))
    yield str(Path(tmp_path).resolve())
    os.chdir(old)


@pytest.fixture
def load_penguin(ip):
    tmp = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv"
    if not Path("penguins.csv").is_file():
        urllib.request.urlretrieve(
            tmp,
            "penguins.csv",
        )
    ip.run_cell("%sql duckdb://")
