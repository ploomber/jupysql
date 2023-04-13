---
jupytext:
  cell_metadata_filter: -all
  formats: md:myst
  notebook_metadata_filter: myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.5
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
myst:
  html_meta:
    description lang=en: Connect to a SQL database from a Jupyter notebook
    keywords: jupyter, sql, jupysql
    property=og:locale: en_US
---

# Connecting to Databases with JupySQL

Learn how to connect to various databases using JupySQL in this tutorial. JupySQL is a Jupyter Notebook extension that allows you to execute SQL queries directly in your notebook cells. We'll show you how to establish connections, connect securely, and use existing `sqlalchemy.engine.Engine` instances.

## Connect with a URL string

Connection strings follow the [SQLAlchemy URL format](http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls). This is the fastest way to connect to your database and the recommended way if you're using SQLite or DuckDB.

However, if you're using a database that requires a password, keep reading for more secure methods.


Database URLs have the following format:

```
dialect+driver://username:password@host:port/database
```

+++

## Building URL strings securely

To connect in a more secure way, you can dynamically build your URL string so your password isn't hardcoded:

```python
from getpass import getpass

password = getpass()
```

When you execute the cell above in a notebook, a text box will appear and whatever you type will be stored in the `password` variable.

```{code-cell} ipython3
# this cell is hidden in the docs, only used to simulate
# the getpass() call
password = "mysupersecretpassword"
```

Then, you can build your connection string:

```{code-cell} ipython3
db_url = f"postgresql://user:{password}@localhost/database"
```

Create an engine and connect:

```{code-cell} ipython3
# this cell is hidden in the docs, only used to fake
# the db_url
db_url = "duckdb://"
```

```{code-cell} ipython3
from sqlalchemy import create_engine

engine = create_engine(db_url)
```

```{code-cell} ipython3
%sql engine
```

```{important}
Unlike `ipython-sql`, JupySQL doesn't allow expanding your database URL with the `$` character:

~~~python
# this doesn't work in JupySQL!
db_url = "dialect+driver://username:password@host:port/database"
%sql $db_url
~~~
```

+++

## Securely storing your password

If you want to store your password securely (and don't get prompted whenever you start a connection), you can use keyring:

```{code-cell} ipython3
%pip install keyring --quiet
```

Execute the following in your notebook:

```{code-cell} ipython3
import keyring

keyring.set_password("my_database", "my_username", "my_password")
```

Then, delete the cell (so your password isn't hardcoded!). Now, you can retrieve your password with:

```{code-cell} ipython3
from sqlalchemy import create_engine
import keyring

password = keyring.get_password("my_database", "my_username")
db_url = f"postgresql://user:{password}@localhost/database"
```

```{code-cell} ipython3
# this cell is hidden in the docs, only used to fake
# the db_url
db_url = "duckdb://"
```

```{code-cell} ipython3
engine = create_engine(db_url)
```

```{code-cell} ipython3
%sql engine
```

```{tip}
If you have issues using `keyring`, send us a message on [Slack.](https://ploomber.io/community)
```

+++

## Passing custom arguments to a URL

+++

Connection arguments not whitelisted by SQLALchemy can be provided with `--connection_arguments`. See [SQLAlchemy Args](https://docs.sqlalchemy.org/en/13/core/engines.html#custom-dbapi-args).

Here's an example using SQLite:

```{code-cell} ipython3
%load_ext sql
```

```{code-cell} ipython3
%sql --connection_arguments '{"timeout":10, "mode":"ro"}' sqlite://
```

## Connecting via an environment variable

+++

Set the `DATABASE_URL` environment variable, and `%sql` will automatically load it. You can do this either by setting the environment variable from your terminal or in your notebook:

```python
from getpass import getpass
from os import environ

password = getpass()
environ["DATABASE_URL"] = f"postgresql://user:{password}@localhost/database"
```

```{code-cell} ipython3
# this cell is hidden in the docs, only used to fake
# the environment variable
from os import environ
environ["DATABASE_URL"] = "sqlite://"
```

```{code-cell} ipython3
%sql
```

## Using an existing `sqlalchemy.engine.Engine`

You can use an existing `Engine` by passing the variable name to `%sql`.

```{code-cell} ipython3
import pandas as pd
from sqlalchemy.engine import create_engine
```

```{code-cell} ipython3
engine = create_engine("sqlite://")
```

```{code-cell} ipython3
df = pd.DataFrame({"x": range(5)})
df.to_sql("numbers", engine)
```

```{code-cell} ipython3
%load_ext sql
```

```{code-cell} ipython3
%sql engine
```

```{code-cell} ipython3
%%sql
SELECT * FROM numbers
```

## Using a URL object

+++

## Configuration file


```{tip} 
It is recommended to use config file for connection as it's more secure and do not expose credentials.
```

To ensure the security of your credentials, you can store connection information in a configuration file, under a section name chosen to  refer to your database.

For instance, suppose you have a configuration file named _dsn.ini_ that contains the following section:

```
[DB_CONFIG_1] 
drivername=postgres 
host=my.remote.host 
port=5433 
database=mydatabase 
username=myuser 
password=1234
```

```{important}
Leave your configuration file out of your git repository by adding it to the `.gitignore` file!
```

then you can establish a connection to your database by running the following commands:

```
%config SqlMagic.dsn_filename='./dsn.ini'
%sql --section DB_CONFIG_1 
```

+++

## Tutorials

Vendor-specific details are available in our tutorials:

- [PostgreSQL](integrations/postgres-connect)
- [ClickHouse](integrations/clickhouse)
- [MariaDB](integrations/mariadb)
- [MindsDB](integrations/mindsdb)
- [MSSQL](integrations/mssql)
- [MySQL](integrations/mysql)
