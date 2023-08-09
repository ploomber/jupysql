from sql import display
from sql import util
from sql.store_utils import get_all_keys
from sql.exceptions import RuntimeError, TableNotFoundError


ORIGINAL_ERROR = "\nOriginal error message from DB driver:\n"
CTE_MSG = (
    "If using snippets, you may pass the --with argument explicitly.\n"
    "For more details please refer: "
    "https://jupysql.ploomber.io/en/latest/compose.html#with-argument"
)
POSTGRES_MSG = """\nLooks like you have run into some issues.
                Review our DB connection via URL strings guide:
                https://jupysql.ploomber.io/en/latest/connecting.html .
                 Using Ubuntu? Check out this guide: "
                https://help.ubuntu.com/community/PostgreSQL#fe_sendauth:_
                no_password_supplied\n"""


class ErrorHandler:
    """Encapsulates the error handling logic and displays descriptive
    messages to the user.
    """

    def __init__(self, error, query=None, short_error=True):
        self.error = error
        self.query = query
        self.short_error = short_error

    def _snippet_typo_error_message(self):
        """Function to generate message for possible
        snippets if snippet name in user query is a
        typo
        """
        if self.query:
            tables = util.extract_tables_from_query(self.query)
            for table in tables:
                suggestions = util.find_close_match(table, get_all_keys())
                err_message = f"There is no table with name {table!r}."
                if len(suggestions) > 0:
                    suggestions_message = util.get_suggestions_message(suggestions)
                    return f"{err_message}{suggestions_message}"
        return ""

    def _is_postgres_pwd_error(self):
        return "fe_sendauth: no password supplied" in str(self.error)

    def _detailed_message_with_error_type(self):
        """Function to generate descriptive error message.
        Currently it handles syntax error messages, table not found messages
        and password issue when connecting to postgres
        """
        original_error = str(self.error)
        syntax_error_substrings = [
            "syntax error",
            "error in your sql syntax",
            "incorrect syntax",
            "invalid sql",
        ]
        not_found_substrings = [
            "does not exist",
            "not found",
            "could not find",
            "no such table",
        ]
        if util.if_substring_exists(original_error.lower(), syntax_error_substrings):
            return f"{CTE_MSG}\n\n{ORIGINAL_ERROR}{original_error}\n", RuntimeError
        elif util.if_substring_exists(original_error.lower(), not_found_substrings):
            typo_err_msg = self._snippet_typo_error_message()
            if typo_err_msg:
                return (
                    f"{CTE_MSG}\n\n{typo_err_msg}\n\n"
                    f"{ORIGINAL_ERROR}{original_error}\n",
                    TableNotFoundError,
                )
            else:
                return f"{CTE_MSG}\n\n{ORIGINAL_ERROR}{original_error}\n", RuntimeError
        elif self._is_postgres_pwd_error():
            return f"{POSTGRES_MSG}\n{ORIGINAL_ERROR}{original_error}\n", RuntimeError
        return None, None

    def _display_error_msg_with_trace(self, message):
        """Displays the detailed error message and prints
        original stack trace as well."""
        if message is not None:
            display.message(message)
        self.error.modify_exception = True
        raise self.error

    def _raise_error(self, message, error_type):
        """Raise specific error from the detailed message. If detailed
        message is None reraise original error"""
        if message is not None:
            raise error_type(message) from self.error
        else:
            raise RuntimeError(str(self.error)) from self.error

    def handle_exception(self):
        """
        This function is the entry point for detecting error type
        and handling it accordingly.
        """
        if util.is_sqlalchemy_error(self.error) or util.is_non_sqlalchemy_error(
            self.error
        ):
            detailed_message, error_type = self._detailed_message_with_error_type()
            if self.short_error:
                self._raise_error(detailed_message, error_type)
            else:
                self._display_error_msg_with_trace(detailed_message)
        else:
            raise self.error
