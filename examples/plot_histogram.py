import urllib.request

# this requires duckdb: pip install duckdb
import duckdb

from sql import plot


urllib.request.urlretrieve(
    "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv",
    "penguins.csv",
)

conn = duckdb.connect(database=":memory:")

plot.histogram("penguins.csv", "body_mass_g", bins=50, conn=conn)
