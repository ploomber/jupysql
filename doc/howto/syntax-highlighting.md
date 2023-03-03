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

+++ {"tags": []}

# SQL syntax highlighting

+++ {"tags": []}

You can enable SQL syntax highlighting via [Jupyterlab-lsp](https://github.com/jupyter-lsp/jupyterlab-lsp).

+++ {"tags": []}

## Installation

```{code-cell} ipython3
conda install --channel conda-forge nodejs
```

```{code-cell} ipython3
%pip install jupysql jupyter-lsp jupyterlab-lsp python-language-server --quiet
```

+++ {"tags": []}

#### 2. Install [Jupyterlab-lsp](https://github.com/krassowski/jupyterlab-lsp):

+++ {"tags": []}

#### 3. Install Jupyterlab-lsp-server:

+++ {"tags": []}

```bash
pip install python-lsp-server[all]
```

+++ {"tags": []}

#### 4. Install [JupySQL](https://github.com/ploomber/jupysql) to run sql queries

+++ {"tags": []}

```bash
!pip install jupysql
```

```{code-cell} ipython3
jlpm add --dev sql-language-server
```

+++ {"tags": []}

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
