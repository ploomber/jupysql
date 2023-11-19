import pandas as pd


def test_query_count(ip_with_trino, test_table_name_dict):
    out = ip_with_trino.run_cell(
        f"%sql SELECT * FROM default.{test_table_name_dict['taxi']} LIMIT 3"
    ).result.DataFrame()

    assert len(out) == 3


def test_persist(ip_with_trino, test_table_name_dict):
    ip_with_trino.run_cell("%config SqlMagic.autopandas=True")

    df = pd.DataFrame({"a": [1, 2, 3]})
    ip_with_trino.push({"df": df})
    ip_with_trino.run_cell("%sql --persist-replace default.df --no-index")
    persisted = ip_with_trino.run_cell(
        "%sql SELECT DISTINCT a FROM default.df ORDER BY a"
    ).result
    assert persisted == [(0, 1, "foo"), (1, 2, "bar")]
