# Sql syntex highlighting

This repository demonstrated how to highlight the sql syntex in JupyterLab with [Jupyterlab-lsp](https://github.com/krassowski/jupyterlab-lsp).

## Installation

#### 1. Install JupyterLab with pip:

```bash
pip install jupyterlab
```
Note: The verson of JupyterLab >=3.3.0,<4.0

#### 2. Install [Jupyterlab-lsp](https://github.com/krassowski/jupyterlab-lsp):

```bash
pip install jupyter-lsp
```

#### 3. Install Jupyterlab-lsp-server:

```bash
pip install python-lsp-server[all]
```

#### 4. Install [ipython-sql](https://github.com/catherinedevlin/ipython-sql) to run sql queries

```bash
pip install ipython-sql
```
Notes: Depending on the specific database you’re using, you may need to install one of the following libraries by typing the following command into any Jupyter cell:

For example:
1. SQLite
```bash
pip install sqlite3
```
2. Mysql
```bash
pip install sql
```

#### 5. Once installed, launch JupyterLab with:

```bash
jupyter-lab
```

## Setup
Load the extension:

```python
%load_ext sql
```

## Querying
Then we can do sql sytex hightlighting in JupyterLab, here are some querying examples:

```python
%%sql
SELECT * FROM sometable WHERE x>= 1;
```