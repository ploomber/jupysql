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

# Querying JSON files

In this tutorial, we'll show you how to query JSON with JupySQL and DuckDB.

note: add info on other formats: .jsonl, .jsonl.gz

```{code-cell} ipython3
from pathlib import Path
import json

data = [
    {"name": "John", "age": 25,  "friends": ["Jake", "Kelly"], "likes": {"pizza": True}},
    {"name": "Jake", "age": 20,  "friends": ["John"], "likes": {"pizza": False}},
    {"name": "Kelly", "age": 21,  "friends": ["John", "Sam"], "likes": {"pizza": True}},
    {"name": "Sam", "age": 22,  "friends": ["Kelly"], "likes": {"pizza": False}},
]

lines = ""

for d in data:
    lines += json.dumps(d) + "\n"

Path("people.json").write_text(lines)
```

```{code-cell} ipython3
cat people.json
```

## Query

Load the extension and start a DuckDB in-memory database:

```{code-cell} ipython3
%load_ext sql
%sql duckdb://
```

Read the JSON data:

```{code-cell} ipython3
%%sql
SELECT *
FROM read_json_objects('people.json')
```

## Extract fields

Extract fields from each JSON record:

```{code-cell} ipython3
%%sql
SELECT
    json ->> '$.name' AS name,
    json ->> '$.friends[0]' AS first_friend,
    json ->> '$.likes.pizza' AS likes_pizza,
FROM read_json_objects('people.json')
```

## Extract schema

Infer the JSON schema:

```{code-cell} ipython3
%%sql
SELECT
    json_structure(json),
    json_structure(json ->> '$.likes'),
FROM read_json_objects('people.json')
```

```{code-cell} ipython3
%%sql schema <<
SELECT
    json_structure(json) AS schema_all,
    json_structure(json ->> '$.likes') AS schema_likes,
FROM read_json_objects('people.json')
```

Pretty print the inferred schema:

```{code-cell} ipython3
from rich import print_json
```

```{code-cell} ipython3
row = schema.DataFrame().iloc[0]
print_json(row.schema_all)
print_json(row.schema_likes)
```

## Store snippets

You can use JupySQL's `--save` feature to store a SQL snippet so you can keep your queries succint:

```{code-cell} ipython3
%%sql --save clean_data
SELECT
    json ->> '$.name' AS name,
    json ->> '$.friends[0]' AS first_friend,
    json ->> '$.likes.pizza' AS likes_pizza,
FROM read_json_objects('people.json')
```

```{code-cell} ipython3
%%sql --with clean_data
SELECT * FROM clean_data
```

```{code-cell} ipython3

```
