from IPython.display import display


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
