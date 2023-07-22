from pathlib import Path
import urllib.request

from sql.connection import SQLAlchemyConnection

from sql import plot


if not Path("iris.csv").is_file():
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/plotly/datasets/master/iris-data.csv",
        "iris.csv",
    )

conn = SQLAlchemyConnection.from_connect_str("duckdb://")

# returns matplotlib.Axes object
ax = plot.boxplot("iris.csv", "petal width", conn=conn)
ax.set_title("My custom title")
ax.grid()
