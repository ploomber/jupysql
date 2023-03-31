---
jupytext:
  notebook_metadata_filter: myst
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

# `%sqlcmd tables`

This section demonstrates how to use `%sqlcmd tables` to list tables.

## `%sqlcmd tables` Example

The data from the `.csv` file must first be registered as a table in order for the table to be listed.

```{code-cell} ipython3
%%sql
CREATE TABLE penguins AS SELECT * FROM penguins.csv
```

The cell above allows the data to now be listed as a table from the following code:

```{code-cell} ipython3
%sqlcmd tables
```
# `%sqlcmd columns`

This section demonstrates how to use `%sqlcmd tables` to list tables.

## `%sqlcmd columns` Example

After either registering the data as a table, their respective columns can now be listed with the following code:

```{code-cell} ipython3
%sqlcmd columns -t penguins
```

