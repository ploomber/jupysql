try:
    from pgspecial.main import PGSpecial
except ModuleNotFoundError:
    PGSpecial = None

from sql import exceptions


def handle_postgres_special(conn, statement):
    """Execute a PostgreSQL special statement using PGSpecial module."""
    if not PGSpecial:
        raise exceptions.MissingPackageError("pgspecial not installed")

    pgspecial = PGSpecial()
    # TODO: support for raw psycopg2 connections
    _, cur, headers, _ = pgspecial.execute(
        conn.connection_sqlalchemy.connection.cursor(), statement
    )[0]
    return FakeResultProxy(cur, headers)


class FakeResultProxy(object):
    """A fake class that pretends to behave like the ResultProxy from
    SqlAlchemy.
    """

    def __init__(self, cursor, headers):
        if cursor is None:
            cursor = []
            headers = []
        if isinstance(cursor, list):
            self.from_list(source_list=cursor)
        else:
            self.fetchall = cursor.fetchall
            self.fetchmany = cursor.fetchmany
            self.rowcount = cursor.rowcount
        self.keys = lambda: headers
        self.returns_rows = True

    def from_list(self, source_list):
        "Simulates SQLA ResultProxy from a list."

        self._source_list = source_list
        self._pos = 0
        self.rowcount = len(source_list)

        def fetchall():
            remaining = self._source_list[self._pos :]
            self._pos = len(self._source_list)
            return remaining

        def fetchmany(size):
            result = self._source_list[self._pos : self._pos + size]
            self._pos += len(result)
            return result

        self.fetchall = fetchall
        self.fetchmany = fetchmany

    def close(self):
        pass
