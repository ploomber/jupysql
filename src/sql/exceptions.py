from IPython.core import error


def exception_factory(name):
    def _error(message):
        exc = error.UsageError(message)
        exc.error_type = name
        return exc

    return _error


ArgumentError = exception_factory("ArgumentError")
TableNotFoundError = exception_factory("TableNotFoundError")
MissingPackageError = exception_factory("MissingPackageError")
TypeError = exception_factory("TypeError")
RuntimeError = exception_factory("RuntimeError")
