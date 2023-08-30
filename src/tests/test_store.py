import pytest
from sql.connection import SQLAlchemyConnection, ConnectionManager
from IPython.core.error import UsageError
from sql import store
from sqlalchemy import create_engine


@pytest.fixture(autouse=True)
def setup_no_current_connect(monkeypatch):
    monkeypatch.setattr(ConnectionManager, "current", None)


@pytest.fixture
def ip_snippets(ip):
    ip.run_cell(
        """
%%sql --save a --no-execute
SELECT *
FROM number_table
"""
    )
    ip.run_cell(
        """
            %%sql --save b --no-execute
            SELECT *
            FROM a
            WHERE x > 5
            """
    )
    ip.run_cell(
        """
            %%sql --save c --no-execute
            SELECT *
            FROM a
            WHERE x < 5
            """
    )
    yield ip


def test_sqlstore_setitem():
    sql_store = store.SQLStore()
    sql_store["a"] = "SELECT * FROM a"
    assert sql_store["a"] == "SELECT * FROM a"


def test_sqlstore_getitem_success():
    sql_store = store.SQLStore()
    sql_store["first"] = "SELECT * FROM a"
    assert sql_store["first"] == "SELECT * FROM a"


@pytest.mark.parametrize(
    "key, expected_error",
    [
        (
            "second",
            (
                '"second" is not a valid snippet identifier.'
                ' Valid identifiers are "first".'
            ),
        ),
        (
            "firs",
            '"firs" is not a valid snippet identifier. Did you mean "first"?',
        ),
    ],
    ids=[
        "invalid-key",
        "close-match-key",
    ],
)
def test_sqlstore_getitem(key, expected_error):
    sql_store = store.SQLStore()
    sql_store["first"] = "SELECT * FROM a"

    with pytest.raises(UsageError) as excinfo:
        sql_store[key]

    assert excinfo.value.error_type == "UsageError"
    assert str(excinfo.value) == expected_error


def test_sqlstore_getitem_with_multiple_existing_snippets():
    sql_store = store.SQLStore()
    sql_store["first"] = "SELECT * FROM a"
    sql_store["first2"] = "SELECT * FROM a"

    with pytest.raises(UsageError) as excinfo:
        sql_store["second"]

    assert excinfo.value.error_type == "UsageError"
    assert (
        str(excinfo.value)
        == '"second" is not a valid snippet identifier. '
        + 'Valid identifiers are "first", "first2".'
    )


def test_hyphen():
    sql_store = store.SQLStore()

    with pytest.raises(UsageError) as excinfo:
        store.SQLQuery(sql_store, "SELECT * FROM a", with_=["first-"])

    assert "Using hyphens is not allowed." in str(excinfo.value)


def test_key():
    sql_store = store.SQLStore()

    with pytest.raises(UsageError) as excinfo:
        sql_store.store("first", "SELECT * FROM first WHERE x > 20", with_=["first"])

    assert "cannot appear in with_ argument" in str(excinfo.value)


@pytest.mark.parametrize(
    "is_dialect_support_backtick",
    [(True), (False)],
)
@pytest.mark.parametrize(
    "with_",
    [
        ["third"],
        ["first", "third"],
        ["first", "third", "first"],
        ["third", "first"],
    ],
    ids=[
        "simple",
        "redundant",
        "duplicated",
        "redundant-end",
    ],
)
def test_serial(with_, is_dialect_support_backtick, monkeypatch):
    """To test if SQLStore can store multiple with sql clause
    and parse into final combined sql clause

    Parameters
    ----------
    with_ : string
        The key to use in with sql clause
    is_dialect_support_backtick : bool
        If the current connected dialect support `(backtick) syntax
    monkeypatch : Monkeypatch
        A convenient fixture for monkey-patching
    """
    conn = SQLAlchemyConnection(engine=create_engine("sqlite://"))

    monkeypatch.setattr(
        conn,
        "is_use_backtick_template",
        lambda: is_dialect_support_backtick,
    )
    identifier = "`" if is_dialect_support_backtick else ""

    sql_store = store.SQLStore()
    sql_store.store("first", "SELECT * FROM a WHERE x > 10")
    sql_store.store("second", "SELECT * FROM first WHERE x > 20", with_=["first"])

    sql_store.store(
        "third", "SELECT * FROM second WHERE x > 30", with_=["second", "first"]
    )

    result = sql_store.render("SELECT * FROM third", with_=with_)

    assert (
        str(result)
        == "WITH {0}first{0} AS (SELECT * FROM a WHERE x > 10), \
{0}second{0} AS (SELECT * FROM first WHERE x > 20), \
{0}third{0} AS (SELECT * FROM second WHERE x > 30)SELECT * FROM third".format(
            identifier
        )
    )


@pytest.mark.parametrize(
    "is_dialect_support_backtick",
    [(True), (False)],
)
def test_branch_root(is_dialect_support_backtick, monkeypatch):
    """To test if SQLStore can store multiple with sql clause,
    but with each with clause has it's own sub-query.
    To see if SQLStore can parse into final combined sql clause

    Parameters
    ----------
    with_ : string
        The key to use in with sql clause
    is_dialect_support_backtick : bool
        If the current connected dialect support `(backtick) syntax
    monkeypatch : Monkeypatch
        A convenient fixture for monkey-patching
    """
    conn = SQLAlchemyConnection(engine=create_engine("sqlite://"))
    monkeypatch.setattr(
        conn,
        "is_use_backtick_template",
        lambda: is_dialect_support_backtick,
    )
    identifier = "`" if is_dialect_support_backtick else ""

    sql_store = store.SQLStore()
    sql_store.store("first_a", "SELECT * FROM a WHERE x > 10")
    sql_store.store("second_a", "SELECT * FROM first_a WHERE x > 20", with_=["first_a"])
    sql_store.store(
        "third_a", "SELECT * FROM second_a WHERE x > 30", with_=["second_a"]
    )

    sql_store.store("first_b", "SELECT * FROM b WHERE y > 10")

    result = sql_store.render("SELECT * FROM third", with_=["third_a", "first_b"])
    assert (
        str(result)
        == "WITH {0}first_a{0} AS (SELECT * FROM a WHERE x > 10), \
{0}second_a{0} AS (SELECT * FROM first_a WHERE x > 20), \
{0}third_a{0} AS (SELECT * FROM second_a WHERE x > 30), \
{0}first_b{0} AS (SELECT * FROM b WHERE y > 10)SELECT * FROM third".format(
            identifier
        )
    )


@pytest.mark.parametrize(
    "is_dialect_support_backtick",
    [(True), (False)],
)
def test_branch_root_reverse_final_with(is_dialect_support_backtick, monkeypatch):
    """To test if SQLStore can store multiple with sql clause,
    but with different reverse order in with_ parameter.
    To see if SQLStore can parse into final combined sql clause

    Parameters
    ----------
    with_ : string
        The key to use in with sql clause
    is_dialect_support_backtick : bool
        If the current connected dialect support `(backtick) syntax
    monkeypatch : Monkeypatch
        A convenient fixture for monkey-patching
    """
    conn = SQLAlchemyConnection(engine=create_engine("sqlite://"))

    monkeypatch.setattr(
        conn,
        "is_use_backtick_template",
        lambda: is_dialect_support_backtick,
    )
    identifier = "`" if is_dialect_support_backtick else ""

    sql_store = store.SQLStore()

    sql_store.store("first_a", "SELECT * FROM a WHERE x > 10")
    sql_store.store("second_a", "SELECT * FROM first_a WHERE x > 20", with_=["first_a"])
    sql_store.store(
        "third_a", "SELECT * FROM second_a WHERE x > 30", with_=["second_a"]
    )

    sql_store.store("first_b", "SELECT * FROM b WHERE y > 10")

    result = sql_store.render("SELECT * FROM third", with_=["first_b", "third_a"])
    assert (
        str(result)
        == "WITH {0}first_a{0} AS (SELECT * FROM a WHERE x > 10), \
{0}second_a{0} AS (SELECT * FROM first_a WHERE x > 20), \
{0}first_b{0} AS (SELECT * FROM b WHERE y > 10), \
{0}third_a{0} AS (SELECT * FROM second_a WHERE x > 30)SELECT * FROM third".format(
            identifier
        )
    )


@pytest.mark.parametrize(
    "is_dialect_support_backtick",
    [(True), (False)],
)
def test_branch(is_dialect_support_backtick, monkeypatch):
    """To test if SQLStore can store multiple with sql clause,
    but some sub-queries have same with_ dependency.
    To see if SQLStore can parse into final combined sql clause

    Parameters
    ----------
    with_ : string
        The key to use in with sql clause
    monkeypatch : Monkeypatch
        A convenient fixture for monkey-patching
    """
    conn = SQLAlchemyConnection(engine=create_engine("sqlite://"))

    monkeypatch.setattr(
        conn,
        "is_use_backtick_template",
        lambda: is_dialect_support_backtick,
    )
    identifier = "`" if is_dialect_support_backtick else ""

    sql_store = store.SQLStore()

    sql_store.store("first_a", "SELECT * FROM a WHERE x > 10")
    sql_store.store("second_a", "SELECT * FROM first_a WHERE x > 20", with_=["first_a"])
    sql_store.store(
        "third_a", "SELECT * FROM second_a WHERE x > 30", with_=["second_a"]
    )

    sql_store.store(
        "first_b", "SELECT * FROM second_a WHERE y > 10", with_=["second_a"]
    )

    result = sql_store.render("SELECT * FROM third", with_=["first_b", "third_a"])
    assert (
        str(result)
        == "WITH {0}first_a{0} AS (SELECT * FROM a WHERE x > 10), \
{0}second_a{0} AS (SELECT * FROM first_a WHERE x > 20), \
{0}first_b{0} AS (SELECT * FROM second_a WHERE y > 10), \
{0}third_a{0} AS (SELECT * FROM second_a WHERE x > 30)SELECT * FROM third".format(
            identifier
        )
    )


def test_get_all_keys(ip_snippets):
    keys = store.get_all_keys()
    assert "a" in keys
    assert "b" in keys
    assert "c" in keys


def test_get_key_dependents(ip_snippets):
    keys = store.get_key_dependents("a")
    assert "b" in keys
    assert "c" in keys


def test_del_saved_key(ip_snippets):
    keys = store.del_saved_key("c")
    assert "a" in keys
    assert "b" in keys


def test_del_saved_key_error(ip_snippets):
    with pytest.raises(UsageError) as excinfo:
        store.del_saved_key("non_existent_key")
    assert "No such saved snippet found : non_existent_key" in str(excinfo.value)
