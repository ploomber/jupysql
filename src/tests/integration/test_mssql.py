import pyodbc


def test_query_count(ip_with_MSSQL, excepted, request):
    # MSSQL doesn't have LIMIT
    out = ip_with_MSSQL.run_line_magic(
        "sql",
        """
        SELECT *
        FROM taxi
        ORDER BY 1
        OFFSET 0 ROWS FETCH NEXT 3 ROWS ONLY
        """,
    )

    assert len(out) == excepted


def test_create_table_with_indexed_df(ip_with_MSSQL, excepted, request):
    # MSSQL gives error if DB doesn't exist
    try:
        ip_with_MSSQL.run_cell("%sql DROP TABLE new_table_from_df")
    except pyodbc.ProgrammingError as e:
        print(f"Error: {e}")

    # Prepare DF
    ip_with_MSSQL.run_cell(
        """results = %sql\
                    SELECT *\
                    FROM taxi\
                    ORDER BY 1\
                    OFFSET 0 ROWS FETCH NEXT 15 ROWS ONLY
                    """
    )
    ip_with_MSSQL.run_cell("new_table_from_df = results.DataFrame()")
    # Create table from DF
    persist_out = ip_with_MSSQL.run_cell("%sql --persist new_table_from_df")
    query_out = ip_with_MSSQL.run_cell("%sql SELECT * FROM new_table_from_df")
    assert persist_out.error_in_exec is None and query_out.error_in_exec is None
    assert len(query_out.result) == excepted
