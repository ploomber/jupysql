import urllib.request

from sql.connection import SQLAlchemyConnection

from sql import plot


urllib.request.urlretrieve(
    "https://raw.githubusercontent.com/plotly/datasets/master/iris-data.csv",
    "iris.csv",
)

conn = SQLAlchemyConnection.from_connect_str("duckdb://")

plot.histogram("iris.csv", "petal width", bins=50, conn=conn)
