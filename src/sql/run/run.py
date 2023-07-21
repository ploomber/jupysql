import sqlparse

from sql import exceptions, display
from sql.run.resultset import ResultSet
from sql.run.pgspecial import handle_postgres_special


# some dialects have autocommit
# specific dialects break when commit is used:
_COMMIT_BLACKLIST_DIALECTS = (
    "athena",
    "bigquery",
    "clickhouse",
    "ingres",
    "mssql",
    "teradata",
    "vertica",
)


def run_statements(conn, sql, config):
    """
    Run a SQL query (supports running multiple SQL statements) with the given
    connection. This is the function that's called when executing SQL magic.

    Parameters
    ----------
    conn : sql.connection.Connection
        The connection to use

    sql : str
        SQL query to execution

    config
        Configuration object
    """
    if not sql.strip():
        # returning only when sql is empty string
        return "Connected: %s" % conn.name

    for statement in sqlparse.split(sql):
        first_word = sql.strip().split()[0].lower()

        # attempting to run a transaction
        if first_word == "begin":
            raise exceptions.RuntimeError("JupySQL does not support transactions")

        # postgres metacommand
        if first_word.startswith("\\") and is_postgres_or_redshift(conn.dialect):
            result = handle_postgres_special(conn, statement)

        # regular query
        else:
            result = conn.raw_execute(statement)
            _apply_commit(conn=conn, config=config)

            if result and config.feedback:
                if hasattr(result, "rowcount"):
                    display_affected_rowcount(result.rowcount)

    resultset = ResultSet(result, config, statement, conn)
    return select_df_type(resultset, config)


def display_affected_rowcount(rowcount):
    if rowcount > 0:
        display.message_success(f"{rowcount} rows affected.")


def _apply_commit(conn, config):
    """Issues a commit, if appropriate for current config and dialect"""

    # TODO: maybe remove this?
    _should_commit = config.autocommit and all(
        dialect not in str(conn.dialect) for dialect in _COMMIT_BLACKLIST_DIALECTS
    )

    if _should_commit:
        conn_ = conn.connection

        try:
            conn_.commit()
        except Exception:
            display.message(
                "The database does not support the COMMIT command. "
                "You can disable autocommit with %config SqlMagic.autocommit=False"
            )


def is_postgres_or_redshift(dialect):
    """Checks if dialect is postgres or redshift"""
    return "postgres" in str(dialect) or "redshift" in str(dialect)


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
