---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.4
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

+++

# SQL syntax highlighting

+++

You can enable SQL syntax highlighting via [Jupyterlab-lsp](https://github.com/jupyter-lsp/jupyterlab-lsp).

+++

## Installation

```sh
conda create --name jupysqlenv python=3.10 jupyterlab --yes -c conda-forge
conda activate jupysqlenv
```

```{code-cell} ipython3
conda install --channel conda-forge nodejs --yes
```

```{code-cell} ipython3
pip install jupyter-lsp jupyterlab-lsp python-language-server --quiet
```

+++

#### 2. Install [Jupyterlab-lsp](https://github.com/krassowski/jupyterlab-lsp):

+++

#### 3. Install Jupyterlab-lsp-server:

+++


+++

#### 4. Install [JupySQL](https://github.com/ploomber/jupysql) to run sql queries

+++

```bash
pip install jupysql --quiet
```

```{code-cell} ipython3
jlpm add sql-language-server
```

+++

## Setup
Load the extension:

```{code-cell} ipython3
:tags: []

%load_ext sql
```

```{code-cell} ipython3
%sql duckdb://
```

## Querying
Then we can do sql sytex hightlighting in JupyterLab, here are some querying examples:

```{code-cell} ipython3
%%sql
INSTALL httpfs
```

```{code-cell} ipython3
%%sql 
SELECT *
FROM "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv"
LIMIT 3
```

```{code-cell} ipython3

```
