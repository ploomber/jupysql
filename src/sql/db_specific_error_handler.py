ORIGINAL_ERROR = "\nOriginal error message from DB driver:\n"
CTE_MSG = (
    "If using snippets, you may pass the --with argument explicitly.\n"
    "For more details please refer: "
    "https://jupysql.ploomber.io/en/latest/compose.html#with-argument"
)

DB_ERRORS = [
    "duckdb.CatalogException",
    "duckdb.ParserException",
    "Parser Error",
    "ORA",
    "oracle",
    "pyodbc.ProgrammingError",
]


def _is_syntax_error(error):
    """
    Function to detect whether error message from DB driver
    is related to syntax error in user query.
    """
    error_lower = error.lower()
    return (
        "syntax error" in error_lower
        or "error in your sql syntax" in error_lower
        or "incorrect syntax" in error_lower
        or "invalid" in error_lower
    )


def _is_table_not_found_error(error):
    """
    Function to detect whether error message from DB driver
    is due to non-existent table.
    """
    error_lower = error.lower()
    return (
        ("does not exist" in error_lower)
        or "not found" in error_lower
        or "could not find" in error_lower
    )


def detail_db(original_error):
    original_error = str(original_error)
    if any(msg in original_error for msg in DB_ERRORS) and (
        _is_syntax_error(original_error) or _is_table_not_found_error(original_error)
    ):
        return f"{CTE_MSG}\n\n{ORIGINAL_ERROR}{original_error}\n"

    return None
