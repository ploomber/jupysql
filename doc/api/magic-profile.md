---
jupytext:
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
    description lang=en: Documentation for the %sqlcmd profile
    keywords: jupyter, sql, jupysql, sqlcmd, profile
    property=og:locale: en_US
---

# `%sqlcmd profile`

`%sqlcmd profile` allows you to summarize a table quickly.

+++

## Load Data

```{code-cell} ipython3
%load_ext sql
%sql duckdb://
```

```{code-cell} ipython3
from pathlib import Path
from urllib.request import urlretrieve

if not Path("penguins.csv").is_file():
    urlretrieve(
        "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv",
        "penguins.csv",
    )
```

```{code-cell} ipython3
%%sql
SELECT * FROM penguins.csv LIMIT 3
```

Let's save the file penguins.csv as a table penguins.

```{code-cell} ipython3
:tags: [hide-output]

%%sql 
DROP TABLE IF EXISTS penguins;
CREATE SCHEMA IF NOT EXISTS s1;
CREATE TABLE s1.penguins (
    species VARCHAR(255),
    island VARCHAR(255),
    bill_length_mm DECIMAL(5, 2),
    bill_depth_mm DECIMAL(5, 2),
    flipper_length_mm DECIMAL(5, 2),
    body_mass_g INTEGER,
    sex VARCHAR(255)
);

COPY s1.penguins FROM 'penguins.csv' WITH (FORMAT CSV, HEADER TRUE);
```

## `%sqlcmd profile`

+++

Returns the information of a table.

+++

Arguments:

`-t`/`--table` (Required) Get the profile of a table

`-s`/`--schema` (Optional) Get the profile of a table under a specified schema

`-o`/`--output` (Optional) Output the profile at a specified location (path name expected)

```{code-cell} ipython3
%sqlcmd profile -t s1.penguins
```

```{code-cell} ipython3
%sqlcmd profile -s s1 -t penguins
```

The output of these two command should be the same. However, look at how we specify the table name differently (whether or not we specify the schema) to get a better sense of the schema argument.

```{code-cell} ipython3
%sqlcmd profile -t s1.penguins -o penguins-profile.html
```
