from sql.magic import SqlMagic
from IPython import InteractiveShell
import duckdb
from pandas import DataFrame
import numpy as np

num_rows = 1000_000

df = DataFrame(np.random.randn(num_rows, 20))

magic = SqlMagic(InteractiveShell())

conn = duckdb.connect()
magic.execute(line="conn --alias duckdb", local_ns={"conn": conn})
magic.autopandas = True
magic.displaycon = False


@profile  # noqa
def run_magic():
    magic.execute("SELECT * FROM df")


if __name__ == "__main__":
    run_magic()
