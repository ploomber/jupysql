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
    description lang=en: Convert outputs from SQL queries to pandas data frames using
      JupySQL
    keywords: jupyter, sql, jupysql, pandas
    property=og:locale: en_US
---

# Oracle Database

This tutorial will show you how to get a Oracle instance up and running locally to test JupySQL. You can run this in a Jupyter notebook.

+++

## Pre-requisites

To run this tutorial, you need to install following Python packages:

```{code-cell} ipython3
%pip install oracledb --quiet
```

## Start Oracle instance

We use the non-official image [gvenzl/oracle-xe](https://hub.docker.com/r/gvenzl/oracle-xe) to initial the  instance, and database users (this will take 1-2 minutes):

```{code-cell} ipython3
%%bash 
docker run --name postgres -d -p 1521:1521 \
  -e ORACLE_PASSWORD=ploomber_app_admin_password \
  -e APP_USER=ploomber_app \
  -e APP_USER_PASSWORD=ploomber_app_password gvenzl/oracle-xe
```

## Load sample data

Now, let's fetch some sample data. We'll be using the [NYC taxi dataset](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page):

```{code-cell} ipython3
import pandas as pd

df = pd.read_csv(
    "https://github.com/Muhd-Shahid/Write-Raw-"
    "File-into-Database-Server/raw/main/iris.csv",
    index_col=False,
)
df.shape
```

```{code-cell} ipython3
from sqlalchemy import create_engine
from sqlalchemy.types import Float, Text

engine = create_engine(
    "oracle+oracledb://ploomber_app:ploomber_app_password"
    "@localhost:1521/?service_name=XEPDB1"
)
df.to_sql(
    name="iris",
    con=engine,
    chunksize=1000,
    if_exists="replace",
    index=False,
    dtype={
        "sepal_length": Float(),
        "sepal_width": Float(),
        "petal_length": Float(),
        "petal_width": Float(),
        "species": Text()
    },
)
engine.dispose()
```

## Query

Now, let's start JuppySQL, authenticate and start querying the data!

```{code-cell} ipython3
%load_ext sql
```

```{code-cell} ipython3
%sql oracle+oracledb://ploomber_app:ploomber_app_password@localhost:1521/?service_name=XEPDB1
```

List the tables in the database:

```{code-cell} ipython3
%sqlcmd tables
```

List columns in the taxi table:

```{code-cell} ipython3
%sqlcmd columns --table iris
```

```{code-cell} ipython3
%sql SELECT * FROM iris
```

Query our data:

```{code-cell} ipython3
%%sql
SELECT COUNT(*) FROM iris
```

## Parametrize queries

```{code-cell} ipython3
threshold = 5.0
```

```{code-cell} ipython3
%%sql
SELECT COUNT(*) FROM iris
WHERE sepal_length < {{threshold}}
```

```{code-cell} ipython3
threshold = 6.0
```

```{code-cell} ipython3
%%sql
SELECT COUNT(*) FROM iris
WHERE sepal_length < {{threshold}}
```

## CTEs

```{code-cell} ipython3
%%sql --save saved_cte --no-execute
SELECT * FROM iris
WHERE sepal_length > 6.0
```

```{code-cell} ipython3
%sql --with saved_cte SELECT * FROM saved_cte
```

This is what JupySQL executes:
