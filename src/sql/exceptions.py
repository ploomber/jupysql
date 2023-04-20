from IPython.core import error


def TableNotFoundError(message):
    exc = error.UsageError(message)
    exc.error_type = "TableNotFoundError"
    return exc
