from sql import inspect
import difflib
import sql.run
from sql.connection import Connection


def convert_to_scientific(value):
    """
    Converts value to scientific notation if necessary

    Parameters
    ----------
    value : any
        Value to format.
    """
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and _is_long_number(value)
    ):
        new_value = "{:,.3e}".format(value)

    else:
        new_value = value

    return new_value


def _is_long_number(num) -> bool:
    """
    Checks if num's digits > 10
    """
    if "." in str(num):
        split_by_decimal = str(num).split(".")
        if len(split_by_decimal[0]) > 10 or len(split_by_decimal[1]) > 10:
            return True
    return False


def is_table_exists(table, schema=None, ignore_error=False) -> bool:
    """
    Check if given table exists for a given connection

    Parameters
    ----------
    table: str
        Table name

    schema: str, default None
        Schema name

    ignore_error: bool, default False
        Avoid raising a ValueError
    """
    if table is None:
        raise ValueError("Table cannot be None")

    if schema:
        table_ = f"{schema}.{table}"
    else:
        table_ = table

    _is_exist = False
    try:
        sql.run.raw_run(Connection.current, f"SELECT * FROM {table_} WHERE 1=0")
        _is_exist = True
    except Exception:
        if not ignore_error:
            expected = []
            existing_schemas = inspect.get_schema_names()
            if schema and schema not in existing_schemas:
                expected = existing_schemas
                invalid_input = schema
            else:
                existing_tables = _get_list_of_existing_tables()
                expected = existing_tables
                invalid_input = table

            if schema:
                err_message = (
                    f"There is no table with name {table!r} in schema {schema!r}"
                )
            else:
                err_message = (
                    f"There is no table with name {table!r} in the default schema"
                )

            suggestions = difflib.get_close_matches(invalid_input, expected)

            if len(suggestions) > 0:
                _suggestions_string = pretty_print(suggestions, last_delimiter="or")
                err_message += f"\nDid you mean : {_suggestions_string}"

            raise ValueError(err_message)

    return _is_exist


def _get_list_of_existing_tables() -> list:
    """
    Returns a list of table names for a given connection
    """
    tables = []
    tables_rows = inspect.get_table_names()._table
    for row in tables_rows:
        table_name = row.get_string(fields=["Name"], border=False, header=False).strip()

        tables.append(table_name)
    return tables


def pretty_print(obj, delimiter=",", last_delimiter="and", repr_=False) -> str:
    """
    Returns a formatted string representation of an array
    """
    if repr_:
        sorted_ = sorted(repr(element) for element in obj)
    else:
        sorted_ = sorted(f"'{element}'" for element in obj)

    if len(sorted_) > 1:
        sorted_[-1] = f"{last_delimiter} {sorted_[-1]}"

    return f"{delimiter} ".join(sorted_)
