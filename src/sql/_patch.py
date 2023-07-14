import sys
import types
from sql import display


def show_usage_error(self, exc):
    """
    This is a patched version of IPython's InteractiveShell.show_usage_error,
    which allows us to pass a custom prefix in the error message.
    """
    if hasattr(exc, "error_type"):
        display.message(f"{exc.error_type}: {exc}", file=sys.stderr)
    else:
        display.message(f"UsageError: {exc}", file=sys.stderr)


def patch_ipython_usage_error(ip):
    """Patch IPython so we can customize UsageError's messages"""
    ip.show_usage_error = types.MethodType(show_usage_error, ip)
