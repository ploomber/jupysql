import os
from difflib import get_close_matches
import atexit

import sqlalchemy
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchModuleError, OperationalError
from IPython.core.error import UsageError
import difflib
import sqlglot


from sql.store import store
from sql.telemetry import telemetry
from sql import exceptions, display
from sql.error_message import detail
from ploomber_core.exceptions import modify_exceptions

PLOOMBER_DOCS_LINK_STR = (
    "Documentation: https://jupysql.ploomber.io/en/latest/connecting.html"
)
IS_SQLALCHEMY_ONE = int(sqlalchemy.__version__.split(".")[0]) == 1

# Check Full List: https://docs.sqlalchemy.org/en/20/dialects
MISSING_PACKAGE_LIST_EXCEPT_MATCHERS = {
    # SQLite
    "sqlite": "sqlite",
    "pysqlcipher3": "pysqlcipher3",
    # DuckDB
    "duckdb": "duckdb-engine",
    # MySQL + MariaDB
    "pymysql": "pymysql",
    "mysqldb": "mysqlclient",
    "mariadb": "mariadb",
    "mysql": "mysql-connector-python",
    "asyncmy": "asyncmy",
    "aiomysql": "aiomysql",
    "cymysql": "cymysql",
    "pyodbc": "pyodbc",
    # PostgreSQL
    "psycopg2": "psycopg2",
    "psycopg": "psycopg",
    "pg8000": "pg8000",
    "asyncpg": "asyncpg",
    "psycopg2cffi": "psycopg2cffi",
    # Oracle
    "cx_oracle": "cx_oracle",
    "oracledb": "oracledb",
    # MSSQL
    "pyodbc": "pyodbc",
    "pymssql": "pymssql",
}

DIALECT_NAME_SQLALCHEMY_TO_SQLGLOT_MAPPING = {"postgresql": "postgres", "mssql": "tsql"}

# All the DBs and their respective documentation links
DB_DOCS_LINKS = {
    "duckdb": "https://jupysql.ploomber.io/en/latest/integrations/duckdb.html",
    "mysql": "https://jupysql.ploomber.io/en/latest/integrations/mysql.html",
    "mssql": "https://jupysql.ploomber.io/en/latest/integrations/mssql.html",
    "mariadb": "https://jupysql.ploomber.io/en/latest/integrations/mariadb.html",
    "clickhouse": "https://jupysql.ploomber.io/en/latest/integrations/clickhouse.html",
    "postgresql": (
        "https://jupysql.ploomber.io/en/latest/integrations/postgres-connect.html"
    ),
    "questdb": "https://jupysql.ploomber.io/en/latest/integrations/questdb.html",
}


def extract_module_name_from_ModuleNotFoundError(e):
    return e.name


def extract_module_name_from_NoSuchModuleError(e):
    return str(e).split(":")[-1].split(".")[-1]


"""
When there is ModuleNotFoundError or NoSuchModuleError case
Three types of suggestions will be shown when the missing module name is:
1. Excepted in the pre-defined map, suggest the user to install the driver pkg
2. Closely matched to the pre-defined map, suggest the user to type correct driver name
3. Not found in the pre-defined map, suggest user to use valid driver pkg
"""


def get_missing_package_suggestion_str(e):
    suggestion_prefix = "To fix it, "
    module_name = None
    if isinstance(e, ModuleNotFoundError):
        module_name = extract_module_name_from_ModuleNotFoundError(e)
    elif isinstance(e, NoSuchModuleError):
        module_name = extract_module_name_from_NoSuchModuleError(e)

    module_name = module_name.lower()
    # Excepted
    for matcher, suggested_package in MISSING_PACKAGE_LIST_EXCEPT_MATCHERS.items():
        if matcher == module_name:
            return suggestion_prefix + "try to install package: " + suggested_package
    # Closely matched
    close_matches = difflib.get_close_matches(
        module_name, MISSING_PACKAGE_LIST_EXCEPT_MATCHERS.keys()
    )
    if close_matches:
        return f'Perhaps you meant to use driver the dialect: "{close_matches[0]}"'
    # Not found
    return (
        suggestion_prefix + "make sure you are using correct driver name:\n"
        "Ref: https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls"
    )


def rough_dict_get(dct, sought, default=None):
    """
    Like dct.get(sought), but any key containing sought will do.

    If there is a `@` in sought, seek each piece separately.
    This lets `me@server` match `me:***@myserver/db`
    """

    sought = sought.split("@")
    for key, val in dct.items():
        if not any(s.lower() not in key.lower() for s in sought):
            return val
    return default


class ConnectionMixin:
    """Shared functionality between SQLAlchemy and DBAPI connections"""

    def __init__(self, alias):
        self.alias = alias

        ConnectionManager.current = self
        ConnectionManager.connections[self.alias or self.url] = self

        self._result_sets = []

    def _get_curr_sqlalchemy_connection_info(self):
        """Get the dialect, driver, and database server version info of current
        connected dialect

        Returns
        -------
        dict
            The dictionary which contains the SQLAlchemy-based dialect
            information, or None if there is no current connection.
        """

        if not self.session:
            return None

        try:
            engine = self._metadata.bind if IS_SQLALCHEMY_ONE else self.session
        except Exception:
            engine = self.session

        return {
            "dialect": getattr(engine.dialect, "name", None),
            "driver": getattr(engine.dialect, "driver", None),
            "server_version_info": getattr(engine.dialect, "server_version_info", None),
        }

    # TODO: we have self.dialect and we also have this, which is confusing, see #732
    def _get_curr_sqlglot_dialect(self):
        """Get the dialect name in sqlglot package scope

        Returns
        -------
        str
            Available dialect in sqlglot package, see more:
            https://github.com/tobymao/sqlglot/blob/main/sqlglot/dialects/dialect.py
        """
        connection_info = self._get_curr_sqlalchemy_connection_info()
        if not connection_info:
            return None

        return DIALECT_NAME_SQLALCHEMY_TO_SQLGLOT_MAPPING.get(
            connection_info["dialect"], connection_info["dialect"]
        )

    def close(self):
        """Close the current connection"""
        for rs in self._result_sets:
            rs._sqlaproxy.close()

        self.session.close()

    def _transpile_query(self, query):
        """Translate the given SQL clause that's compatible to current connected
        dialect by sqlglot

        Parameters
        ----------
        query : str
            Original SQL clause

        Returns
        -------
        str
            SQL clause that's compatible to current connected dialect
        """
        write_dialect = self._get_curr_sqlglot_dialect()
        try:
            query = sqlglot.parse_one(query).sql(dialect=write_dialect)
        finally:
            return query

    def _prepare_query(self, query, with_=None) -> str:
        """
        Returns a textual representation of a query based
        on the current connection

        Parameters
        ----------
        query : str
            SQL query

        with_ : string, default None
            The key to use in with sql clause
        """
        if with_:
            query = str(store.render(query, with_=with_))

        query = self._transpile_query(query)

        if self.is_dbapi_connection:
            query = str(query)
        else:
            query = sqlalchemy.sql.text(query)

        return query

    def execute(self, query, with_=None):
        """
        Executes SQL query on a given connection
        """
        query = self._prepare_query(query, with_)
        return self.session.execute(query)

    def is_use_backtick_template(self):
        """Get if the dialect support backtick (`) syntax as identifier

        Returns
        -------
        bool
            Indicate if the dialect can use backtick identifier in the SQL clause
        """
        cur_dialect = self._get_curr_sqlglot_dialect()
        if not cur_dialect:
            return False
        try:
            return (
                "`" in sqlglot.Dialect.get_or_raise(cur_dialect).Tokenizer.IDENTIFIERS
            )
        except (ValueError, AttributeError, TypeError):
            return False

    def get_curr_identifiers(self) -> list:
        """
        Returns list of identifiers for current connection

        Default identifiers are : ["", '"']
        """
        identifiers = ["", '"']
        try:
            connection_info = self._get_curr_sqlalchemy_connection_info()
            if connection_info:
                cur_dialect = connection_info["dialect"]
                identifiers_ = sqlglot.Dialect.get_or_raise(
                    cur_dialect
                ).Tokenizer.IDENTIFIERS

                identifiers = [*set(identifiers + identifiers_)]
        except ValueError:
            pass
        except AttributeError:
            # this might be a DBAPI connection
            pass

        return identifiers


class ConnectionManager:
    """A class to manage and create database connections"""

    # all connections
    connections = {}

    # the active connection
    current = None

    @classmethod
    def set(cls, descriptor, displaycon, connect_args=None, creator=None, alias=None):
        """
        Set the current database connection. This method is called from the magic to
        determine which connection to use (either use an existing one or open a new one)
        """
        connect_args = connect_args or {}

        if descriptor:
            if isinstance(descriptor, Connection):
                cls.current = descriptor
            elif isinstance(descriptor, Engine):
                cls.current = Connection(descriptor, alias=alias)
            elif is_pep249_compliant(descriptor):
                cls.current = DBAPIConnection(descriptor, alias=alias)
            else:
                existing = rough_dict_get(cls.connections, descriptor)
                # NOTE: I added one indentation level, otherwise
                # the "existing" variable would not exist if
                # passing an engine object as descriptor.
                # Since I never saw this breaking, my guess
                # is that we're missing some unit tests
                # when descriptor is a connection object
                # http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#custom-dbapi-connect-arguments # noqa
                # if same alias found
                if existing and existing.alias == alias:
                    cls.current = existing
                # if just switching connections
                elif existing and alias is None:
                    cls.current = existing
                # if new alias connection
                elif existing is None or existing.alias != alias:
                    cls.current = cls.from_connect_str(
                        connect_str=descriptor,
                        connect_args=connect_args,
                        creator=creator,
                        alias=alias,
                    )

        else:
            if cls.connections:
                if displaycon:
                    cls.display_current_connection()
            elif os.getenv("DATABASE_URL"):
                cls.current = cls.from_connect_str(
                    connect_str=os.getenv("DATABASE_URL"),
                    connect_args=connect_args,
                    creator=creator,
                    alias=alias,
                )
            else:
                raise cls._error_no_connection()
        return cls.current

    @classmethod
    def close_all(cls, verbose=False):
        """Close all connections"""
        connections = ConnectionManager.connections.copy()
        for name, conn in connections.items():
            conn.close()

            if verbose:
                display.message(f"Closing {name}")

        cls.connections = {}

    @classmethod
    def _error_no_connection(cls):
        """Error when there isn't any connection"""
        err = UsageError("No active connection." + _suggest_fix(env_var=True))
        err.modify_exception = True
        return err

    @classmethod
    def display_current_connection(cls):
        for conn in cls._get_connections():
            if conn["current"]:
                alias = conn.get("alias")
                if alias:
                    display.message(f"Running query in {alias!r}")
                else:
                    display.message(f"Running query in {conn['url']!r}")

    @classmethod
    def _get_connections(cls):
        """
        Return a list of dictionaries
        """
        connections = []

        for key in sorted(cls.connections):
            conn = cls.connections[key]

            is_current = conn == cls.current

            connections.append(
                {
                    "current": is_current,
                    "key": key,
                    "url": conn.url,
                    "alias": conn.alias,
                    "connection": conn,
                }
            )

        return connections

    @classmethod
    def close_connection_with_descriptor(cls, descriptor):
        """Close a connection with the given descriptor"""
        if isinstance(descriptor, Connection):
            conn = descriptor
        else:
            conn = cls.connections.get(descriptor) or cls.connections.get(
                descriptor.lower()
            )
        if not conn:
            raise exceptions.RuntimeError(
                "Could not close connection because it was not found amongst these: %s"
                % str(list(cls.connections.keys()))
            )

        if descriptor in cls.connections:
            cls.connections.pop(descriptor)
        else:
            cls.connections.pop(
                str(conn.metadata.bind.url) if IS_SQLALCHEMY_ONE else str(conn.url)
            )
            conn.session.close()

    @classmethod
    def connections_table(cls):
        """Returns the current connections as a table"""
        connections = cls._get_connections()

        def map_values(d):
            d["current"] = "*" if d["current"] else ""
            d["alias"] = d["alias"] if d["alias"] else ""
            return d

        return display.ConnectionsTable(
            headers=["current", "url", "alias"],
            rows_maps=[map_values(c) for c in connections],
        )

    @classmethod
    def from_connect_str(
        cls, connect_str=None, connect_args=None, creator=None, alias=None
    ):
        """Creates a new connection from a connection string"""
        connect_args = connect_args or {}

        try:
            if creator:
                engine = sqlalchemy.create_engine(
                    connect_str,
                    connect_args=connect_args,
                    creator=creator,
                )
            else:
                engine = sqlalchemy.create_engine(
                    connect_str,
                    connect_args=connect_args,
                )
        except (ModuleNotFoundError, NoSuchModuleError) as e:
            suggestion_str = get_missing_package_suggestion_str(e)
            raise exceptions.MissingPackageError(
                "\n\n".join(
                    [
                        str(e),
                        suggestion_str,
                        PLOOMBER_DOCS_LINK_STR,
                    ]
                )
            ) from e
        except Exception as e:
            raise cls._error_invalid_connection_info(e, connect_str) from e

        connection = Connection(engine, alias=alias)
        connection.connect_args = connect_args

        return connection


class Connection(ConnectionMixin):
    """Manages connections to databases

    Parameters
    ----------
    engine: sqlalchemy.engine.Engine
        The SQLAlchemy engine to use

    Attributes
    ----------
    alias : str or None
        The alias passed in the constructor

    engine : sqlalchemy.engine.Engine
        The SQLAlchemy engine passed to the constructor

    name : str
        A name to identify the connection: {user}@{database_name}

    metadata : Metadata or None
        An SQLAlchemy Metadata object (if using SQLAlchemy 2, this is None),
        used to retrieve connection information

    url : str
        An obfuscated connection string (password hidden)

    dialect : sqlalchemy dialect
        A SQLAlchemy dialect object

    session : sqlalchemy session
        A SQLAlchemy session object
    """

    is_dbapi_connection = False

    def __init__(self, engine, alias=None):
        self.engine = engine
        self.name = self.assign_name(engine)

        self.url = (
            repr(sqlalchemy.MetaData(bind=engine).bind.url)
            if IS_SQLALCHEMY_ONE
            else repr(engine.url)
        )

        self.dialect = engine.url.get_dialect()
        self.session = self._create_session(engine, self.url)

        super().__init__(alias=alias)

        if IS_SQLALCHEMY_ONE:
            self._metadata = sqlalchemy.MetaData(bind=engine)
        else:
            self._metadata = None

    @classmethod
    @modify_exceptions
    def _create_session(cls, engine, connect_str):
        try:
            session = engine.connect()
            return session
        except OperationalError as e:
            detailed_msg = detail(e)
            if detailed_msg is not None:
                raise exceptions.UsageError(detailed_msg)
            else:
                print(e)
        except Exception as e:
            raise cls._error_invalid_connection_info(e, connect_str) from e

    @classmethod
    def _error_invalid_connection_info(cls, e, connect_str):
        err = UsageError(
            "An error happened while creating the connection: "
            f"{e}.{_suggest_fix(env_var=False, connect_str=connect_str)}"
        )
        err.modify_exception = True
        return err

    @classmethod
    def assign_name(cls, engine):
        name = "%s@%s" % (engine.url.username or "", engine.url.database)
        return name


atexit.register(ConnectionManager.close_all, verbose=True)


class DBAPISession:
    """
    A session object for generic DBAPI connections
    """

    def __init__(self, connection, engine):
        self.engine = engine
        self.dialect = dict(
            {
                "name": connection.dialect,
                "driver": connection.dialect,
                "server_version_info": connection.dialect,
            }
        )

    # TODO: this will fail when using a duck native connection and a tmp
    # table since the table will only be visible to the cursor
    def execute(self, query):
        cur = self.engine.cursor()
        cur.execute(query)
        return cur

    def close(self):
        pass


class DBAPIConnection(ConnectionMixin):
    """
    A connection object for generic DBAPI connections
    """

    is_dbapi_connection = True

    @telemetry.log_call("DBAPIConnection", payload=True)
    def __init__(self, payload, engine=None, alias=None):
        try:
            payload["engine"] = type(engine)
        except Exception as e:
            payload["engine_parsing_error"] = str(e)

        if engine is None:
            raise ValueError("Engine cannot be None")

        # detect if the engine is a native duckdb connection
        _is_duckdb_native = _check_if_duckdb_dbapi_connection(engine)
        connection_name_ = "duckdb" if _is_duckdb_native else "custom_driver"

        if _is_duckdb_native:
            self.url = "duckdb"
        else:
            self.url = str(engine)

        self.name = connection_name_
        self.dialect = connection_name_
        self.session = DBAPISession(self, engine)

        super().__init__(alias=alias)


def _check_if_duckdb_dbapi_connection(conn):
    """Check if the connection is a native duckdb connection"""
    # NOTE: duckdb defines df and pl to efficiently convert results to
    # pandas.DataFrame and polars.DataFrame respectively
    return hasattr(conn, "df") and hasattr(conn, "pl")


def _suggest_fix(env_var, connect_str=None):
    """
    Returns an error message that we can display to the user
    to tell them how to pass the connection string
    """
    DEFAULT_PREFIX = "\n\n"
    prefix = ""

    if connect_str:
        matches = get_close_matches(
            connect_str, list(ConnectionManager.connections), n=1
        )
        matches_db = get_close_matches(
            connect_str.lower(), list(DB_DOCS_LINKS.keys()), cutoff=0.3, n=1
        )

        if matches:
            prefix = prefix + (
                "\n\nPerhaps you meant to use the existing "
                f"connection: %sql {matches[0]!r}?"
            )

        if matches_db:
            prefix = prefix + (
                f"\n\nPerhaps you meant to use the {matches_db[0]!r} db \n"
                f"To find more information regarding connection: "
                f"{DB_DOCS_LINKS[matches_db[0]]}\n\n"
            )

        if not matches and not matches_db:
            prefix = DEFAULT_PREFIX
    else:
        matches = None
        matches_db = None
        prefix = DEFAULT_PREFIX

    connection_string = (
        "Pass a valid connection string:\n    "
        "Example: %sql postgresql://username:password@hostname/dbname"
    )

    suffix = "To fix it:" if not matches else "Otherwise, try the following:"
    options = [f"{prefix}{suffix}", connection_string]

    keys = list(ConnectionManager.connections.keys())

    if keys:
        keys_ = ",".join(repr(k) for k in keys)
        options.append(
            f"Pass a connection key (one of: {keys_})"
            f"\n    Example: %sql {keys[0]!r}"
        )

    if env_var:
        options.append("Set the environment variable $DATABASE_URL")

    if len(options) >= 3:
        options.insert(-1, "OR")

    options.append(PLOOMBER_DOCS_LINK_STR)

    return "\n\n".join(options)


def is_pep249_compliant(conn):
    """
    Checks if given connection object complies with PEP 249
    """
    pep249_methods = [
        "close",
        "commit",
        # "rollback",
        # "cursor",
        # PEP 249 doesn't require the connection object to have
        # a cursor method strictly
        # ref: https://peps.python.org/pep-0249/#id52
    ]

    for method_name in pep249_methods:
        # Checking whether the connection object has the method
        # and if it is callable
        if not hasattr(conn, method_name) or not callable(getattr(conn, method_name)):
            return False

    return True
