---
jupyter:
  jupytext:
    notebook_metadata_filter: myst
    cell_metadata_filter: -all
    formats: md:myst
    text_representation:
      extension: .md
      format_name: myst
      format_version: 0.13
      jupytext_version: 1.14.4
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
  myst:
    html_meta:
      description lang=en: "Read Excel files using Jupysql and query on it"
      keywords: "jupyter, sql, jupysql, excel, xlsx"
      property=og:locale: "en_US"
---

# Loading and Querying Excel Files
In this how-to guide, we are going to use small financial data stored in an Excel file, containing over 700 records. The dataset is publicly available [here](https://go.microsoft.com/fwlink/?LinkID=521962). We are going to use pandas `read_excel` function to read the Excel file and store it in the database using `%sql --persist` command of jupysql.

Installing dependecies:

```{code-cell} ipython3
:tags: [hide-output]

%pip install jupysql duckdb duckdb-engine pandas openpyxl --quiet
```

Reading dataframe using `pandas.read_excel`: 

```{code-cell} ipython3
import pandas as pd
df = pd.read_excel("https://go.microsoft.com/fwlink/?LinkID=521962")
```

Initializing jupysql and connecting to `duckdb` database

```{code-cell} ipython3
%load_ext sql
%sql duckdb://
```

Persisting the dataframe in duckdb database. It is stored in table named `df`.
```{code-cell} ipython3
%sql --persist df
```

## Running some standard queries
- Selecting first 3 queries
    ```{code-cell} ipython3
    %%sql 
    SELECT *
    FROM df
    LIMIT 3
    ```
- Countries in the database
    ```{code-cell} ipython3
    %%sql 
    SELECT DISTINCT Country
    FROM df
    ``` 
- Evaluating total profit country-wise and ordering them in desceding order according to profit.
    ```{code-cell} ipython3
    %%sql
    select Country, SUM(Profit) Total_Profit
    from df
    group by Country
    order by Total_Profit DESC
    ```