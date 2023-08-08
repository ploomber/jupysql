try:
    from jupysql_plugin.widgets import ConnectorWidget
except ModuleNotFoundError:
    ConnectorWidget = None

from ploomber_core.dependencies import requires
from configparser import ConfigParser
import json


@requires(["jupysql_plugin"])
def connect(others):
    """
    Implementation of `%sqlcmd connect`
    """

    connectorwidget = ConnectorWidget()

    config = get_connections_config_file()
    sections = config.sections()
    update_connectorwidget_connect(
        sections[-1], config[sections[-1]]["drivername"], connectorwidget
    )
    update_connectorwidget_stored_conn(config, connectorwidget)

    return connectorwidget


def get_connections_config_file():
    config = ConfigParser()
    config.read("connections.ini")
    return config


def update_connectorwidget_connect(alias, drivername, CONNECTORWIDGET):
    try:
        CONNECTORWIDGET._connect({"name": alias, "driver": drivername})
        CONNECTORWIDGET.send({"method": "connected", "message": alias})
    except Exception as e:
        CONNECTORWIDGET.send_error_message_to_front(e)


def update_connectorwidget_stored_conn(current_config, CONNECTORWIDGET):
    sections = current_config.sections()
    if len(sections) > 0:
        connections = [
            {"name": s, "driver": current_config[s]["drivername"]} for s in sections
        ]

        CONNECTORWIDGET.stored_connections = connections
        CONNECTORWIDGET.send(
            {"method": "update_connections", "message": json.dumps(connections)}
        )
