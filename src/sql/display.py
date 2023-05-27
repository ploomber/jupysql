"""
A module to display confirmation messages and contextual information to the user
"""
from prettytable import PrettyTable
from IPython.display import display


class Table:
    """Represents a table"""

    def __init__(self, headers, rows) -> None:
        self._headers = headers
        self._rows = rows
        self._table = PrettyTable()
        self._table.field_names = headers

        for row in rows:
            self._table.add_row(row)

        self._table_html = self._table.get_html_string()
        self._table_txt = self._table.get_string()

    def __repr__(self) -> str:
        return self._table_txt

    def _repr_html_(self) -> str:
        return self._table_html


class Message:
    """Message for the user"""

    def __init__(self, message, style=None) -> None:
        self._message = message
        self._style = "" or style

    def _repr_html_(self):
        return f'<span style="{self._style}">{self._message}</span>'

    def __repr__(self) -> str:
        return self._message


def message(message):
    """Display a generic message"""
    display(Message(message))


def message_success(message):
    """Display a success message"""
    display(Message(message, style="color: green"))
