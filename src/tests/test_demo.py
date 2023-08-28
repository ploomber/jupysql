from sql.store import store
import pytest


@pytest.fixture
def ip_snippets(ip):
    #for key in list(store):
    #    del store[key]
    ip.run_cell("%sql sqlite://")
    ip.run_cell(
        """
        %%sql --save high_price --no-execute
SELECT *
FROM "test_store"
WHERE price >= 1.50
"""
    )
    ip.run_cell(
        """
        %%sql --save high_price_a --no-execute
SELECT *
FROM "high_price"
WHERE symbol == 'a'
"""
    )
    ip.run_cell(
        """
        %%sql --save high_price_b --no-execute
SELECT *
FROM "high_price"
WHERE symbol == 'b'
"""
    )
    yield ip


def test_snippets(ip_snippets, capsys):
    ip_snippets.run_cell("%sqlcmd snippets")
    captured = capsys.readouterr()

    assert "high_price" in captured.out
    assert "high_price_a" in captured.out
    assert "high_price_b" in captured.out


def test_snippet_without_del(ip_empty, capsys):
    ip_empty.run_cell("%sqlcmd snippets")
    captured = capsys.readouterr()

    assert "No snippets stored" in captured.out


def test_snippets_with_del(ip_empty, capsys):
    from sql.store import store
    for key in list(store):
        del store[key]

    ip_empty.run_cell("%sqlcmd snippets")
    captured = capsys.readouterr()
    assert "No snippets stored" in captured.out