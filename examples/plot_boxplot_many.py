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

plot.boxplot("iris.csv", ["petal width", "sepal width"], conn=conn)
