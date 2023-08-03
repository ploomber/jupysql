---
jupytext:
  notebook_metadata_filter: myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.15.0
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
myst:
  html_meta:
    description lang=en: Documentation for the %sqlcmd tables and %sqlcmd columns
      from JupySQL
    keywords: jupyter, sql, jupysql, tables, columns
    property=og:locale: en_US
---

# `%sqlcmd connect`

`%sqlcmd connect` displays a ConnectorWidget that shows loaded connections through `connections.ini`.

## Installation
Since `%sqlcmd connect` uses an optional `jupysql_plugin` package, please ensure that you have installed the latest version of the JupySQL plugin by running the following command: `pip install jupysql-plugin --upgrade`.

```{code-cell} ipython3
%pip install jupysql_plugin jupyter_server --upgrade --quiet
```

## Store connections in connections.ini

For every connection, the alias should be enclosed within brackets [], followed by the corresponding connection details. When connecting using sqlite or duckdb, only the `drivername` needs to be specified. For postgresql or snowflake connections, the `username`, `password`, `host`, `database`, and `drivername` are required. For mysql or mariadb connections, the `port` also needs to be specified.

```{code-cell} ipython3
from pathlib import Path

# generate connections.ini
Path("connections.ini").write_text(
    """[conn1]
drivername = sqlite

[conn2]
drivername = duckdb
"""
)
```

```{code-cell} ipython3
%load_ext sql
```

## `%sqlcmd connect`

Displays existing connections. Using the provided widget, you can easily connect to a different connection, remove an existing connection, or create a new connection by interacting with the corresponding buttons.

```{code-cell} ipython3
%sqlcmd connect
```

## Current connections

```{code-cell} ipython3
%sql --connections
```
