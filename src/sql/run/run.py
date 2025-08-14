import sqlparse

from sql import exceptions, display
from sql.run.resultset import ResultSet
from sql.run.pgspecial import handle_postgres_special


# TODO: conn also has access to config, we should clean this up to provide a clean
# way to access the config
def run_statements(conn, sql, config, parameters=None):
    """
    Run a SQL query (supports running multiple SQL statements) with the given
    connection. This is the function that's called when executing SQL magic.

    Parameters
    ----------
    conn : sql.connection.AbstractConnection
        The connection to use

    sql : str
        SQL query to execution

    config
        Configuration object

    Examples
    --------

    .. literalinclude:: ../../examples/run_statements.py

    """
    # First, try to extract the usable SQL statements without comments
    statements = list(
        filter(
            lambda stmt: stmt is not None,  # format returns empty tuples
            map(
                lambda stmt: sqlparse.format(stmt, strip_comments=True),
                sqlparse.split(sql),
            ),
        )
    )

    # Handle the empty SQL case
    if not sql.strip() or not statements:
        return "Connected: %s" % conn.name

    # Ensure we have some return value. This maintains type checkers happy
    result = None
    statement = None

    for statement in statements:
        first_word = statement.strip().split()[0].lower()

        if first_word == "begin":
            raise exceptions.RuntimeError("JupySQL does not support transactions")

        # postgres metacommand
        if first_word.startswith("\\") and is_postgres_or_redshift(conn.dialect):
            result = handle_postgres_special(conn, statement)

        # regular query
        else:
            result = conn.raw_execute(statement, parameters=parameters)
            if is_spark(conn.dialect) and config.lazy_execution:
                return result.dataframe

            if (
                config.feedback >= 1
                and hasattr(result, "rowcount")
                and result.rowcount > 0
            ):
                display.message_success(f"{result.rowcount} rows affected.")

    result_set = ResultSet(result, config, statement, conn)
    return select_df_type(result_set, config)


def is_postgres_or_redshift(dialect):
    """Checks if dialect is postgres or redshift"""
    return "postgres" in str(dialect) or "redshift" in str(dialect)


def is_spark(dialect):
    return "spark" in str(dialect)


def select_df_type(resultset, config):
    """
    Converts the input resultset to either a Pandas DataFrame
    or Polars DataFrame based on the config settings.
    """
    if config.autopandas:
        return resultset.DataFrame()
    elif config.autopolars:
        return resultset.PolarsDataFrame(**config.polars_dataframe_kwargs)
    else:
        return resultset
