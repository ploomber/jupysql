import codecs
import csv
import operator
import os.path
import re
from functools import reduce
from io import StringIO
import html

import prettytable
import sqlalchemy
import sqlparse
from sql.connection import Connection
from sqlalchemy.exc import ResourceClosedError
from sql import exceptions, display
from .column_guesser import ColumnGuesserMixin
from sql.warnings import JupySQLDataFramePerformanceWarning

try:
    from pgspecial.main import PGSpecial
except ModuleNotFoundError:
    PGSpecial = None
from sqlalchemy.orm import Session

from sql.telemetry import telemetry
import logging
import warnings
from collections.abc import Iterable

DEFAULT_DISPLAYLIMIT_VALUE = 10


def unduplicate_field_names(field_names):
    """Append a number to duplicate field names to make them unique."""
    res = []
    for k in field_names:
        if k in res:
            i = 1
            while k + "_" + str(i) in res:
                i += 1
            k += "_" + str(i)
        res.append(k)
    return res


class UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        _row = row
        self.writer.writerow(_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)
        self.queue.seek(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class CsvResultDescriptor(object):
    """
    Provides IPython Notebook-friendly output for the
    feedback after a ``.csv`` called.
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def __repr__(self):
        return "CSV results at %s" % os.path.join(os.path.abspath("."), self.file_path)

    def _repr_html_(self):
        return '<a href="%s">CSV results</a>' % os.path.join(
            ".", "files", self.file_path
        )


def _nonbreaking_spaces(match_obj):
    """
    Make spaces visible in HTML by replacing all `` `` with ``&nbsp;``

    Call with a ``re`` match object.  Retain group 1, replace group 2
    with nonbreaking spaces.
    """
    spaces = "&nbsp;" * len(match_obj.group(2))
    return "%s%s" % (match_obj.group(1), spaces)


_cell_with_spaces_pattern = re.compile(r"(<td>)( {2,})")


class ResultSet(ColumnGuesserMixin):
    """
    Results of a SQL query. Fetches rows lazily (only the necessary rows to show the
    preview based on the current configuration)
    """

    _INSTANCES = []

    def __init__(self, sqlaproxy, config, statement=None, dialect=None):
        ResultSet._INSTANCES.append(self)

        self.config = config
        self.truncated = False
        self.sqlaproxy = sqlaproxy
        self.statement = statement

        self._dialect = dialect
        self._keys = None
        self._field_names = None
        self._results = []

        # https://peps.python.org/pep-0249/#description
        self.is_dbapi_results = hasattr(sqlaproxy, "description")

        # note that calling this will fetch the keys
        self.pretty_table = self._init_table()

        self._done_fetching = False

        if self.config.autolimit == 1:
            # if autolimit is 1, we only want to fetch one row
            self.fetchmany(size=1)
            self.did_finish_fetching()
        else:
            # in all other cases, 2 allows us to know if there are more rows
            # for example when creating a table, the results contains one row, in
            # such case, fetching 2 rows will tell us that there are no more rows
            # and can set the _done_fetching flag to True
            self.fetchmany(size=2)

    def extend_results(self, elements):
        self._results.extend(elements)

        # TODO: we should use add_rows but there is a subclass that behaves weirdly
        # so using add_row for now. this is behavior that we inherited from ipython-sql
        for e in elements:
            self.pretty_table.add_row(e)

    def done_fetching(self):
        self._done_fetching = True
        # NOTE: don't close the connection here (self.sqlaproxy.close()),
        # because we need to keep it open for the next query

    def did_finish_fetching(self):
        return self._done_fetching

    @property
    def field_names(self):
        if self._field_names is None:
            self._field_names = unduplicate_field_names(self.keys)

        return self._field_names

    @property
    def keys(self):
        if self._keys is not None:
            return self._keys

        if not self.is_dbapi_results:
            try:
                self._keys = self.sqlaproxy.keys()
            # sqlite raises this error when running a script that doesn't return rows
            # e.g, 'CREATE TABLE' but others don't (e.g., duckdb)
            except ResourceClosedError:
                self._keys = []
                return self._keys

        elif isinstance(self.sqlaproxy.description, Iterable):
            self._keys = [i[0] for i in self.sqlaproxy.description]
        else:
            self._keys = []

        return self._keys

    def _repr_html_(self):
        self.fetch_for_repr_if_needed()

        _cell_with_spaces_pattern = re.compile(r"(<td>)( {2,})")
        if self.pretty_table:
            self.pretty_table.add_rows(self)
            result = self.pretty_table.get_html_string()
            HTML = (
                "%s\n<span style='font-style:italic;font-size:11px'>"
                "<code>ResultSet</code> : to convert to pandas, call <a href="
                "'https://jupysql.ploomber.io/en/latest/integrations/pandas.html'>"
                "<code>.DataFrame()</code></a> or to polars, call <a href="
                "'https://jupysql.ploomber.io/en/latest/integrations/polars.html'>"
                "<code>.PolarsDataFrame()</code></a></span><br>"
            )
            result = HTML % (result)

            # to create clickable links
            result = html.unescape(result)
            result = _cell_with_spaces_pattern.sub(_nonbreaking_spaces, result)
            if self.config.displaylimit != 0:
                HTML = (
                    '%s\n<span style="font-style:italic;text-align:center;">'
                    "Truncated to displaylimit of %d</span>"
                    "<br>"
                    '<span style="font-style:italic;text-align:center;">'
                    "If you want to see more, please visit "
                    '<a href="https://jupysql.ploomber.io/en/latest/api/configuration.html#displaylimit">displaylimit</a>'  # noqa: E501
                    " configuration</span>"
                )
                result = HTML % (result, self.config.displaylimit)
            return result
        else:
            return None

    def __len__(self):
        self.fetchall()

        return len(self._results)

    def __iter__(self):
        self.fetchall()

        for result in self._results:
            yield result

    def __str__(self):
        self.fetch_for_repr_if_needed()
        return str(self.pretty_table)

    def __repr__(self) -> str:
        self.fetch_for_repr_if_needed()
        return str(self.pretty_table)

    def __eq__(self, another: object) -> bool:
        return self._results == another

    def __getitem__(self, key):
        """
        Access by integer (row position within result set)
        or by string (value of leftmost column)
        """
        try:
            return self._results[key]
        except TypeError:
            result = [row for row in self if row[0] == key]
            if not result:
                raise KeyError(key)
            if len(result) > 1:
                raise KeyError('%d results for "%s"' % (len(result), key))
            return result[0]

    def __getattribute__(self, attr):
        "Raises AttributeError when invalid operation is performed."
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            err_msg = (
                f"'{attr}' is not a valid operation, you can convert this "
                "into a pandas data frame by calling '.DataFrame()' or a "
                "polars data frame by calling '.PolarsDataFrame()'"
            )
            raise AttributeError(err_msg) from None

    def dict(self):
        """Returns a single dict built from the result set

        Keys are column names; values are a tuple"""
        return dict(zip(self.keys, zip(*self)))

    def dicts(self):
        "Iterator yielding a dict for each row"
        for row in self:
            yield dict(zip(self.keys, row))

    @telemetry.log_call("data-frame", payload=True)
    def DataFrame(self, payload):
        """Returns a Pandas DataFrame instance built from the result set."""
        payload[
            "connection_info"
        ] = Connection.current._get_curr_sqlalchemy_connection_info()

        has_df_method = hasattr(self.sqlaproxy, "df")

        # native duckdb connection
        if has_df_method:
            # we need to re-execute the statement because if we fetched some rows
            # already, .df() will return None. But only if it's a select statement
            # otherwise we might end up re-execute INSERT INTO or CREATE TABLE
            # statements
            is_select = self.statement.lower().startswith("select")

            if is_select:
                self.sqlaproxy.execute(self.statement)

            return self.sqlaproxy.df()
        else:
            import pandas as pd

            frame = pd.DataFrame(self, columns=(self and self.keys) or [])

            if self._dialect == "duckdb" and not has_df_method and len(frame) >= 1_000:
                warnings.warn(
                    "It looks like you're using DuckDB with SQLAlchemy. "
                    "For faster conversions to pandas.DataFrame, use "
                    " a DuckDB native connection. Docs: {URL}."
                    " to suppress this warning, {CODE}",
                    category=JupySQLDataFramePerformanceWarning,
                )

            return frame

    @telemetry.log_call("polars-data-frame")
    def PolarsDataFrame(self, **polars_dataframe_kwargs):
        """Returns a Polars DataFrame instance built from the result set."""
        has_pl_method = hasattr(self.sqlaproxy, "pl")

        # native duckdb connection
        if hasattr(self.sqlaproxy, "pl"):
            # we need to re-execute the statement because if we fetched some rows
            # already, .df() will return None. But only if it's a select statement
            # otherwise we might end up re-execute INSERT INTO or CREATE TABLE
            # statements
            is_select = self.statement.lower().startswith("select")

            if is_select:
                self.sqlaproxy.execute(self.statement)

            return self.sqlaproxy.pl()
        else:
            import polars as pl

            frame = pl.DataFrame(
                (tuple(row) for row in self),
                schema=self.keys,
                **polars_dataframe_kwargs,
            )

            if self._dialect == "duckdb" and not has_pl_method and len(frame) >= 1_000:
                warnings.warn(
                    "It looks like you're using DuckDB with SQLAlchemy. "
                    "For faster conversions to polars.DataFrame, use "
                    " a DuckDB native connection. Docs: {URL}."
                    " to suppress this warning, {CODE}",
                    category=JupySQLDataFramePerformanceWarning,
                )

            return frame

    @telemetry.log_call("pie")
    def pie(self, key_word_sep=" ", title=None, **kwargs):
        """Generates a pylab pie chart from the result set.

        ``matplotlib`` must be installed, and in an
        IPython Notebook, inlining must be on::

            %%matplotlib inline

        Values (pie slice sizes) are taken from the
        rightmost column (numerical values required).
        All other columns are used to label the pie slices.

        Parameters
        ----------
        key_word_sep: string used to separate column values
                      from each other in pie labels
        title: Plot title, defaults to name of value column

        Any additional keyword arguments will be passed
        through to ``matplotlib.pylab.pie``.
        """
        self.guess_pie_columns(xlabel_sep=key_word_sep)
        import matplotlib.pylab as plt

        ax = plt.gca()

        ax.pie(self.ys[0], labels=self.xlabels, **kwargs)
        ax.set_title(title or self.ys[0].name)
        return ax

    @telemetry.log_call("plot")
    def plot(self, title=None, **kwargs):
        """Generates a pylab plot from the result set.

        ``matplotlib`` must be installed, and in an
        IPython Notebook, inlining must be on::

            %%matplotlib inline

        The first and last columns are taken as the X and Y
        values.  Any columns between are ignored.

        Parameters
        ----------
        title: Plot title, defaults to names of Y value columns

        Any additional keyword arguments will be passed
        through to ``matplotlib.pylab.plot``.
        """
        import matplotlib.pylab as plt

        self.guess_plot_columns()
        self.x = self.x or range(len(self.ys[0]))

        ax = plt.gca()

        coords = reduce(operator.add, [(self.x, y) for y in self.ys])
        ax.plot(*coords, **kwargs)

        if hasattr(self.x, "name"):
            ax.set_xlabel(self.x.name)

        ylabel = ", ".join(y.name for y in self.ys)

        ax.set_title(title or ylabel)
        ax.set_ylabel(ylabel)

        return ax

    @telemetry.log_call("bar")
    def bar(self, key_word_sep=" ", title=None, **kwargs):
        """Generates a pylab bar plot from the result set.

        ``matplotlib`` must be installed, and in an
        IPython Notebook, inlining must be on::

            %%matplotlib inline

        The last quantitative column is taken as the Y values;
        all other columns are combined to label the X axis.

        Parameters
        ----------
        title: Plot title, defaults to names of Y value columns
        key_word_sep: string used to separate column values
                      from each other in labels

        Any additional keyword arguments will be passed
        through to ``matplotlib.pylab.bar``.
        """
        import matplotlib.pylab as plt

        ax = plt.gca()

        self.guess_pie_columns(xlabel_sep=key_word_sep)
        ax.bar(range(len(self.ys[0])), self.ys[0], **kwargs)

        if self.xlabels:
            ax.set_xticks(range(len(self.xlabels)), self.xlabels, rotation=45)

        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ys[0].name)
        return ax

    @telemetry.log_call("generate-csv")
    def csv(self, filename=None, **format_params):
        """Generate results in comma-separated form.  Write to ``filename`` if given.
        Any other parameters will be passed on to csv.writer."""
        if not self.pretty_table:
            return None  # no results

        self.pretty_table.add_rows(self)

        if filename:
            encoding = format_params.get("encoding", "utf-8")
            outfile = open(filename, "w", newline="", encoding=encoding)
        else:
            outfile = StringIO()

        writer = UnicodeWriter(outfile, **format_params)
        writer.writerow(self.field_names)
        for row in self:
            writer.writerow(row)
        if filename:
            outfile.close()
            return CsvResultDescriptor(filename)
        else:
            return outfile.getvalue()

    def fetchmany(self, size):
        """Fetch n results and add it to the results"""
        if not self.did_finish_fetching():
            try:
                returned = self.sqlaproxy.fetchmany(size=size)
            # sqlite raises this error when running a script that doesn't return rows
            # e.g, 'CREATE TABLE' but others don't (e.g., duckdb)
            except ResourceClosedError:
                self.done_fetching()
                return

            self.extend_results(returned)

            if len(returned) < size:
                self.done_fetching()

            if (
                self.config.autolimit is not None
                and self.config.autolimit != 0
                and len(self._results) >= self.config.autolimit
            ):
                self.done_fetching()

    def fetch_for_repr_if_needed(self):
        if self.config.displaylimit == 0:
            self.fetchall()

        missing = self.config.displaylimit - len(self._results)

        if missing > 0:
            self.fetchmany(missing)

    def fetchall(self):
        if not self.did_finish_fetching():
            self.extend_results(self.sqlaproxy.fetchall())
            self.done_fetching()

    def _init_table(self):
        pretty = PrettyTable(self.field_names)

        if isinstance(self.config.style, str):
            _style = prettytable.__dict__[self.config.style.upper()]
            pretty.set_style(_style)

        return pretty


def display_affected_rowcount(rowcount):
    if rowcount > 0:
        display.message_success(f"{rowcount} rows affected.")


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

        self.fetchall = lambda: source_list
        self.rowcount = len(source_list)

        def fetchmany(size):
            pos = 0
            while pos < len(source_list):
                yield source_list[pos : pos + size]
                pos += size

        self.fetchmany = fetchmany


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
            with Session(conn.session) as session:
                session.commit()
        except sqlalchemy.exc.OperationalError:
            print("The database does not support the COMMIT command")


def is_postgres_or_redshift(dialect):
    """Checks if dialect is postgres or redshift"""
    return "postgres" in str(dialect) or "redshift" in str(dialect)


def is_pytds(dialect):
    """Checks if driver is pytds"""
    return "pytds" in str(dialect)


def handle_postgres_special(conn, statement):
    """Execute a PostgreSQL special statement using PGSpecial module."""
    if not PGSpecial:
        raise exceptions.MissingPackageError("pgspecial not installed")

    pgspecial = PGSpecial()
    _, cur, headers, _ = pgspecial.execute(conn.session.connection.cursor(), statement)[
        0
    ]
    return FakeResultProxy(cur, headers)


def set_autocommit(conn, config):
    """Sets the autocommit setting for a database connection."""
    if is_pytds(conn.dialect):
        warnings.warn(
            "Autocommit is not supported for pytds, thus is automatically disabled"
        )
        return False
    if config.autocommit:
        try:
            conn.session.execution_options(isolation_level="AUTOCOMMIT")
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
    # returning only last result, intentionally


def run(conn, sql, config):
    """Run a SQL query with the given connection

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
        manual_commit = False

        # attempting to run a transaction
        if first_word == "begin":
            raise exceptions.RuntimeError("JupySQL does not support transactions")

        # postgres metacommand
        if first_word.startswith("\\") and is_postgres_or_redshift(conn.dialect):
            result = handle_postgres_special(conn, statement)

        # regular query
        else:
            manual_commit = set_autocommit(conn, config)
            is_custom_connection = Connection.is_custom_connection(conn)

            # if regular sqlalchemy, pass a text object
            if not is_custom_connection:
                statement = sqlalchemy.sql.text(statement)

            # edge case: duckdb does dot return a new cursor by default, so if we
            # run conn.session.execute, all pending results from existing resultsets
            # are lost. To avoid this, we first fetch all pending results, then run
            for result in ResultSet._INSTANCES:
                result.fetchall()

            result = conn.session.execute(statement)
            _commit(conn=conn, config=config, manual_commit=manual_commit)

            if result and config.feedback:
                if hasattr(result, "rowcount"):
                    display_affected_rowcount(result.rowcount)

    resultset = ResultSet(result, config, statement, conn._get_curr_sqlglot_dialect())
    return select_df_type(resultset, config)


def raw_run(conn, sql):
    return conn.session.execute(sqlalchemy.sql.text(sql))


class PrettyTable(prettytable.PrettyTable):
    def __init__(self, *args, **kwargs):
        self.row_count = 0
        self.displaylimit = DEFAULT_DISPLAYLIMIT_VALUE
        return super(PrettyTable, self).__init__(*args, **kwargs)

    def add_rows(self, data):
        if self.row_count and (data.config.displaylimit == self.displaylimit):
            return  # correct number of rows already present
        self.clear_rows()
        self.displaylimit = data.config.displaylimit
        if self.displaylimit == 0:
            self.displaylimit = None
        if self.displaylimit in (None, 0):
            self.row_count = len(data)
        else:
            self.row_count = min(len(data), self.displaylimit)
        for row in data[: self.displaylimit]:
            formatted_row = []
            for cell in row:
                if isinstance(cell, str) and cell.startswith("http"):
                    formatted_row.append("<a href={}>{}</a>".format(cell, cell))
                else:
                    formatted_row.append(cell)
            self.add_row(formatted_row)
