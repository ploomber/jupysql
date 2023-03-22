---
jupytext:
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
    description lang=en: Documentation for the %sqlrender magic from JupySQL
    keywords: jupyter, sql, jupysql
    property=og:locale: en_US
---

# `%sqlrender`

```{versionadded} 0.4.3
```

`%sqlrender` helps you compose large SQL queries.

```{code-cell} ipython3
%load_ext sql
```

```{code-cell} ipython3
%sql sqlite:///
```

```{code-cell} ipython3
import pandas as pd
authors = pd.read_csv("https://gist.githubusercontent.com/jaidevd/23aef12e9bf56c618c41/raw/c05e98672b8d52fa0cb94aad80f75eb78342e5d4/books.csv")
```

```{code-cell} ipython3
%sql --persist authors
```

```{code-cell} ipython3
%sql SELECT * FROM authors LIMIT 5
```

## `%sqlrender`

`-w`/`--with` Use a previously saved query as input data

```{code-cell} ipython3
%%sql --save writers_fav --no-execute
SELECT *
FROM authors
WHERE genre = 'data_science'
```

```{code-cell} ipython3
%%sql --save writers_fav_long --no-execute --with writers_fav
SELECT * FROM writers_fav
WHERE Height >= 240
```

```{code-cell} ipython3
query = %sqlrender writers_fav_long --with writers_fav_long
print(query)
```

```{code-cell} ipython3

```
