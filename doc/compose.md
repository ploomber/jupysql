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
myst:
  html_meta:
    description lang=en: "Use JupySQL to organize large SQL queries in a Jupyter notebook"
    keywords: "jupyter, sql, jupysql"
    property=og:locale: "en_US"
---

# Organizing Large Queries


```{dropdown} Required packages
~~~
pip install jupysql matplotlib
~~~
```


*New in version 0.4.3*

```{note}
This is a beta feature, please [join our community](https://ploomber.io/community) and
let us know how we can improve it!
```

Tired of wrangling complex, large-scale SQL queries? JupySQL is here to revolutionize your experience with an intuitive, user-friendly package specifically designed to help you manage and organize large SQL queries in Jupyter Notebooks.

- **Simplify your workflow:** JupySQL allows you to break down large SQL queries into manageable chunks and organize them within your Jupyter Notebook, enhancing readability and maintainability.
- **Modularize your queries:** With JupySQL, you can create reusable query modules and leverage them across your project, promoting code reusability and reducing redundancy.
- **Seamless integration:** JupySQL flawlessly combines the power of SQL with the flexibility of Jupyter Notebooks, offering a one-stop solution for all your data analysis needs.
- **Cross-platform compatibility:** JupySQL supports popular databases like PostgreSQL, MySQL, SQLite, and more, ensuring you can work with any data source.

## Example: record store data

Let's use JupySQL to find the
artists that have produced the largest number of Rock and Metal songs.

Let's load some data:

```{code-cell} ipython3
import urllib.request
from pathlib import Path

if not Path("my.db").is_file():
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"  # noqa
    urllib.request.urlretrieve(url, "my.db")
```

Initialize the extension and set `autolimit=3` so we only retrieve a few rows.

```{code-cell} ipython3
%load_ext sql
```

```{code-cell} ipython3
%config SqlMagic.autolimit = 3
```

Let's see the track-level information:

```{code-cell} ipython3
%%sql sqlite:///my.db
SELECT * FROM Track
```

Let's join track with album and artist to get the artist name and store the query using `--save tracks_with_info`.

*Note: `--save` stores the query, not the data*

```{code-cell} ipython3
%%sql --save tracks_with_info
SELECT t.*, a.title AS album, ar.Name as artist
FROM Track t
JOIN Album a
USING (AlbumId)
JOIN Artist ar
USING (ArtistId)
```

Let's subset the genres we are interested in (Rock and Metal) and save the query.

```{code-cell} ipython3
%%sql --save genres_fav
SELECT * FROM Genre
WHERE Name
LIKE '%rock%'
OR Name LIKE '%metal%' 
```

Now, join genres and tracks, so we only get Rock and Metal tracks. 

Note that we are using `--with`; this will retrieve previously saved queries, and preprend them (using CTEs), then, we save the query in `track_fav` .

```{code-cell} ipython3
%%sql --with genres_fav --with tracks_with_info --save track_fav
SELECT t.*
FROM tracks_with_info t
JOIN genres_fav
ON t.GenreId = genres_fav.GenreId
```

We can now use `track_fav` (which contains Rock and Metal tracks). Let's find which artists have produced the most tracks (and save the query):

```{code-cell} ipython3
%%sql --with track_fav --save top_artist
SELECT artist, COUNT(*) FROM track_fav
GROUP BY artist
ORDER BY COUNT(*) DESC
```

Let's retrieve `top_artist` and plot the results:

```{code-cell} ipython3
top_artist = %sql --with top_artist SELECT * FROM top_artist
top_artist.bar()
```

We can render the full query with the `%sqlrender` magic:

```{code-cell} ipython3
final = %sqlrender top_artist
print(final)
```

We can verify the retrieved query returns the same result:

```{code-cell} ipython3
%%sql
$final
```

## Summary

In the given example, we demonstrated JupySQL's usage as a tool for managing large SQL queries in Jupyter Notebooks. It effectively broke down a complex query into smaller, organized parts, simplifying the process of analyzing a record store's sales database. By using JupySQL, users can easily maintain and reuse their queries, enhancing the overall data analysis experience.