try:
    from jupysql_plugin.widgets import ConnectorWidget

    CONNECTORWIDGET = ConnectorWidget()
except ModuleNotFoundError:
    ConnectorWidget = None
    CONNECTORWIDGET = None

from ploomber_core.dependencies import requires


@requires(["jupysql_plugin"])
def connect(others):
    """
    Implementation of `%sqlcmd connect`
    """

    return CONNECTORWIDGET
