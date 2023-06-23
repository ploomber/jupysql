from sql.sqlcmd import sqlcmd_snippets  # noqa


def execute_snippets_command(others):
    """
    Execution logic for the snippets command

    """
    return sqlcmd_snippets(others)
