import os

import sqlalchemy
from sqlalchemy.engine import Engine
from IPython.core.error import UsageError


class ConnectionError(Exception):
    pass


def rough_dict_get(dct, sought, default=None):
    """
    Like dct.get(sought), but any key containing sought will do.

    If there is a `@` in sought, seek each piece separately.
    This lets `me@server` match `me:***@myserver/db`
    """

    sought = sought.split("@")
    for (key, val) in dct.items():
        if not any(s.lower() not in key.lower() for s in sought):
            return val
    return default


class Connection:
    """Manages connections to databases

    Parameters
    ----------
    engine: sqlalchemy.engine.Engine
        The SQLAlchemy engine to use
    """

    # the active connection
    current = None

    # all connections
    connections = {}

    @classmethod
    def _suggest_fix(cls, env_var):
        """
        Returns an error message that we can display to the user
        to tell them how to pass the connection string
        """
        connection_string = (
            "Pass a valid connection string:\n    "
            "Example: %sql postgresql://username:password@hostname/dbname"
        )
        options = ["\n\nTo fix it:", connection_string]

        keys = list(cls.connections.keys())

        if keys:
            keys_ = ",".join(repr(k) for k in keys)
            options.append(
                f"Pass a connection key (one of: {keys_})"
                f"\n    Example: %sql {keys[0]}"
            )

        if env_var:
            options.append("Set the environment variable $DATABASE_URL")

        if len(options) >= 2:
            options.insert(-1, "OR")

        options.append(
            "If you need help, send us a message: https://ploomber.io/community"
            "\nDocumentation: https://jupysql.ploomber.io/connecting"
        )

        return "\n\n".join(options)

    @classmethod
    def _error_no_connection(cls):
        return UsageError("No active connection." + cls._suggest_fix(env_var=True))

    @classmethod
    def _error_invalid_connection_info(cls, e):
        return UsageError(
            "An error happened while creating the connection: "
            f"{e}. {cls._suggest_fix(env_var=False)}"
        )

    def __init__(self, engine, alias=None):
        self.dialect = engine.url.get_dialect()
        self.metadata = sqlalchemy.MetaData(bind=engine)
        self.name = self.assign_name(engine)
        self.session = engine.connect()
        self.connections[alias or repr(self.metadata.bind.url)] = self
        self.connect_args = None
        self.alias = alias
        Connection.current = self

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
        except Exception as e:
            raise cls._error_invalid_connection_info(e) from e

        connection = cls(engine, alias=alias)
        connection.connect_args = connect_args

        return connection

    @classmethod
    def set(cls, descriptor, displaycon, connect_args=None, creator=None, alias=None):
        """
        Sets the current database connection
        """
        connect_args = connect_args or connect_args

        if descriptor:
            if isinstance(descriptor, Connection):
                cls.current = descriptor
            elif isinstance(descriptor, Engine):
                cls.current = Connection(descriptor)
            else:
                existing = rough_dict_get(cls.connections, descriptor)

                # NOTE: I added one indentation level, otherwise
                # the "existing" variable would not exist if
                # passing an engine object as descriptor.
                # Since I never saw this breaking, my guess
                # is that we're missing some unit tests
                # when descriptor is a connection object
                # http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#custom-dbapi-connect-arguments # noqa
                cls.current = existing or Connection.from_connect_str(
                    connect_str=descriptor,
                    connect_args=connect_args,
                    creator=creator,
                    alias=alias,
                )
        else:

            if cls.connections:
                if displaycon:
                    # display list of connections
                    print(cls.connection_list())
            else:
                if os.getenv("DATABASE_URL"):
                    cls.current = Connection.from_connect_str(
                        connect_str=os.getenv("DATABASE_URL"),
                        connect_args=connect_args,
                        creator=creator,
                        alias=alias,
                    )
                else:
                    raise cls._error_no_connection()

        return cls.current

    @classmethod
    def assign_name(cls, engine):
        name = "%s@%s" % (engine.url.username or "", engine.url.database)
        return name

    @classmethod
    def connection_list(cls):
        result = []
        for key in sorted(cls.connections):
            conn = cls.connections[key]
            engine_url = conn.metadata.bind.url  # type: sqlalchemy.engine.url.URL

            prefix = "* " if conn == cls.current else "  "

            if conn.alias:
                repr_ = f"{prefix} ({conn.alias}) {engine_url!r}"
            else:
                repr_ = f"{prefix} {engine_url!r}"

            result.append(repr_)

        return "\n".join(result)

    @classmethod
    def _close(cls, descriptor):
        if isinstance(descriptor, Connection):
            conn = descriptor
        else:
            conn = cls.connections.get(descriptor) or cls.connections.get(
                descriptor.lower()
            )
        if not conn:
            raise Exception(
                "Could not close connection because it was not found amongst these: %s"
                % str(cls.connections.keys())
            )

        if descriptor in cls.connections:
            cls.connections.pop(descriptor)
        else:
            cls.connections.pop(str(conn.metadata.bind.url))

        conn.session.close()

    def close(self):
        self.__class__._close(self)
