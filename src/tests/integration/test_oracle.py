def test_query_count(ip_with_oracle, test_table_name_dict):
    # MSSQL doesn't have LIMIT
    out = ip_with_oracle.run_line_magic(
        "sql",
        f"""
        SELECT *
        FROM {test_table_name_dict['taxi']} FETCH FIRST 3 ROWS ONLY
        """,
    )

    assert len(out) == 3
