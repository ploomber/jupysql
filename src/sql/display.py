from prettytable import PrettyTable
from IPython.display import display


class Table:
    def __init__(self, headers, rows) -> None:
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
    def __init__(self, message, style=None) -> None:
        self._message = message
        self._style = "" or style

    def _repr_html_(self):
        return f'<i style="{self._style}">{self._message}</i>'

    def __repr__(self) -> str:
        return self._message


def message(message):
    display(Message(message))


def message_success(message):
    display(Message(message, style="color: green"))
