"""
A module to display confirmation messages and contextual information to the user
"""
from prettytable import PrettyTable
from IPython.display import display


class Table:
    """Represents a table"""

    FOOTER = ""

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
        return self._table_txt + "\n" + self.FOOTER

    def _repr_html_(self) -> str:
        return self._table_html + "\n" + self.FOOTER


class ConnectionsTable(Table):
    FOOTER = "Active connections"

    def __init__(self, headers, rows_maps) -> None:
        self._rows_maps = rows_maps

        def get_values(d):
            d = d.copy()
            del d["connection"]
            del d["key"]
            return list(d.values())

        rows = [get_values(r) for r in rows_maps]
        super().__init__(headers=headers, rows=rows)

    def __getitem__(self, key: str):
        """
        This method is provided for backwards compatibility. Before
        creating ConnectionsTable, `%sql --connections` returned a dictionary,
        hence users could retrieve connections using __getitem__
        """
        for row in self._rows_maps:
            if row["key"] == key:
                return row["connection"]


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
