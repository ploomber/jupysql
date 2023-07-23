import sqlparse

from sql import exceptions, display
from sql.run.resultset import ResultSet
from sql.run.pgspecial import handle_postgres_special


# some dialects have autocommit specific dialects break when commit is used
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
    conn : sql.connection.AbstractConnection
        The connection to use

    sql : str
        SQL query to execution

    config
        Configuration object
    """
    if not sql.strip():
        return "Connected: %s" % conn.name

    for statement in sqlparse.split(sql):
        first_word = sql.strip().split()[0].lower()

        # maybe only apply it for duckdb?
        # TODO: add test case when statement starts with "FROM"
        # TODO: add test case when using WITH
        # TODO: checking for with isn't the best idea because it doesn't guarantee
        # that the final one is a select statement
        first_word_statement = statement.strip().split()[0].lower()
        is_select = first_word_statement in {"select", "with"}

        if first_word == "begin":
            raise exceptions.RuntimeError("JupySQL does not support transactions")

        # postgres metacommand
        if first_word.startswith("\\") and is_postgres_or_redshift(conn.dialect):
            result = handle_postgres_special(conn, statement)

        # regular query
        else:
            manual_commit_call_required = set_sqlalchemy_autocommit_option(conn, config)
            result = conn.raw_execute(statement)

            if manual_commit_call_required and not is_select:
                _commit_if_needed(conn=conn, config=config)

            if config.feedback and hasattr(result, "rowcount") and result.rowcount > 0:
                display.message_success(f"{result.rowcount} rows affected.")

    return select_df_type(ResultSet(result, config, statement, conn), config)


def _commit_if_needed(conn, config):
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


# TODO: move this logic to SQLAlchemyConnection
def set_sqlalchemy_autocommit_option(conn, config):
    """
    Sets the autocommit setting for a database connection using SQLAlchemy.
    This better handles some edge cases than calling .commit() on the connection but
    not all drivers support it.
    """
    if is_pytds(conn.dialect):
        return False
    if config.autocommit:
        if conn.is_dbapi_connection:
            return True
        else:
            connection_sqlalchemy = conn.connection_sqlalchemy

            try:
                connection_sqlalchemy.execution_options(isolation_level="AUTOCOMMIT")
            except Exception:
                return True
    return False


def is_pytds(dialect):
    """Checks if driver is pytds"""
    return "pytds" in str(dialect)
