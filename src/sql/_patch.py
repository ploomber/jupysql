import sys
import types


def show_usage_error(self, exc):
    if hasattr(exc, "error_type"):
        print(f"{exc.error_type}: {exc}", file=sys.stderr)
    else:
        print(f"UsageError: {exc}", file=sys.stderr)


def patch_ipython(ip):
    ip.show_usage_error = types.MethodType(show_usage_error, ip)
