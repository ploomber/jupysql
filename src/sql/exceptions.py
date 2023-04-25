from IPython.core import error


def exception_factory(name):
    def _error(message):
        exc = error.UsageError(message)
        exc.error_type = name
        # this attribute will allow the @modify_exceptions decorator to add the
        # community link
        exc.modify_exception = True
        return exc

    return _error


UsageError = exception_factory("UsageError")
TableNotFoundError = exception_factory("TableNotFoundError")
MissingPackageError = exception_factory("MissingPackageError")
TypeError = exception_factory("TypeError")
RuntimeError = exception_factory("RuntimeError")
ValueError = exception_factory("ValueError")
