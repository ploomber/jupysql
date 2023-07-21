import logging
import warnings

import sqlalchemy
from sqlalchemy.orm import Session
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
        manual_commit_call_required = False

        # attempting to run a transaction
        if first_word == "begin":
            raise exceptions.RuntimeError("JupySQL does not support transactions")

        # postgres metacommand
        if first_word.startswith("\\") and is_postgres_or_redshift(conn.dialect):
            result = handle_postgres_special(conn, statement)

        # regular query
        else:
            manual_commit_call_required = set_sqlalchemy_autocommit_option(conn, config)

            result = conn.raw_execute(statement)
            _commit(conn=conn, config=config, manual_commit=manual_commit_call_required)

            if result and config.feedback:
                if hasattr(result, "rowcount"):
                    display_affected_rowcount(result.rowcount)

    resultset = ResultSet(result, config, statement, conn)
    return select_df_type(resultset, config)


def display_affected_rowcount(rowcount):
    if rowcount > 0:
        display.message_success(f"{rowcount} rows affected.")


def _commit(conn, config, manual_commit):
    """Issues a commit, if appropriate for current config and dialect"""

    _should_commit = (
        config.autocommit
        and all(
            dialect not in str(conn.dialect) for dialect in _COMMIT_BLACKLIST_DIALECTS
        )
        and manual_commit
    )

    if _should_commit:
        try:
            with Session(conn.connection) as session:
                session.commit()
        except sqlalchemy.exc.OperationalError:
            display.message("The database does not support the COMMIT command")


def is_postgres_or_redshift(dialect):
    """Checks if dialect is postgres or redshift"""
    return "postgres" in str(dialect) or "redshift" in str(dialect)


def is_pytds(dialect):
    """Checks if driver is pytds"""
    return "pytds" in str(dialect)


# TODO: can we set this when the connection starts? there's no point in running it over
# and over again. also, this gives errors if we're in the middle of a transaction, so
# it's best to call it just once
def set_sqlalchemy_autocommit_option(conn, config):
    """Sets the autocommit setting for a database connection."""
    if is_pytds(conn.dialect):
        warnings.warn(
            "Autocommit is not supported for pytds, thus is automatically disabled"
        )
        return False
    if config.autocommit:
        if conn.is_dbapi_connection:
            logging.debug("AUTOCOMMIT is not supported for DBAPI connections")
        else:
            connection_sqlalchemy = conn.connection_sqlalchemy

            try:
                connection_sqlalchemy.execution_options(isolation_level="AUTOCOMMIT")
            except Exception as e:
                logging.debug(
                    f"The database driver doesn't support such "
                    f"AUTOCOMMIT execution option"
                    f"\nPerhaps you can try running a manual COMMIT command"
                    f"\nMessage from the database driver\n\t"
                    f"Exception:  {e}\n",  # noqa: F841
                )
                return True
    return False


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
