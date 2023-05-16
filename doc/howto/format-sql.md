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
    description lang=en: Format your SQL cells in Jupyter
    keywords: jupyter, jupyterlab, sql
    property=og:locale: en_US
---

# SQL formatting

+++ {"user_expressions": []}

To enable SQL formatting, install `jupysql-plugin`:

```sh
pip install jupysql-plugin --upgrade
```

Then, a "Format SQL" button will appear in JupyterLab:



## Try it out

To try it, click on the 🚀 button at the top of this page, then click on Binder:

![format](../static/launch-on-binder.png)

Then, wait for JupyterLab to load. Once it loads, click on "Format SQL" and you'll see that the SQL cell below is formatted!

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
%load_ext sql
%sql duckdb://
```

```{code-cell} ipython3
%%sql
select * from penguins.csv where island = 'Torgersen' limit 3
```
