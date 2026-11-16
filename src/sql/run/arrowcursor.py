from datetime import timedelta


def intervals_to_durations(table):
    """
    Convert month_day_nano_interval columns to duration[us] (a month counts as 30
    days, like psycopg2 and duckdb do) since polars cannot import them and rows
    would contain pyarrow MonthDayNano objects instead of timedelta
    """
    import pyarrow as pa

    for i, field in enumerate(table.schema):
        if field.type != pa.month_day_nano_interval():
            continue
        values = [
            (
                None
                if v is None
                else timedelta(
                    days=v.months * 30 + v.days, microseconds=v.nanoseconds // 1000
                )
            )
            for v in table.column(i).to_pylist()
        ]
        table = table.set_column(
            i, field.with_type(pa.duration("us")), pa.array(values, pa.duration("us"))
        )
    return table


class ArrowCursor:
    """
    Wraps an ADBC DBAPI cursor so results are read as Arrow record batches.
    Rows are only materialized for what is fetched via fetchone/fetchmany/fetchall,
    and fetch_arrow_table returns every row (including the ones already fetched)
    without converting to Python objects.
    """

    def __init__(self, cursor):
        self._cursor = cursor
        self._reader = None
        self._schema = None
        self._batches = []
        self._table = None
        self._buffered = 0
        self._offset = 0
        self._exhausted = False

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def _ensure_reader(self):
        if self._reader is None and not self._exhausted:
            if self._cursor.description is None:
                raise RuntimeError("no results to fetch")
            self._reader = self._cursor.fetch_record_batch()
            self._schema = self._reader.schema

    def _read_until(self, n_rows):
        self._ensure_reader()
        while not self._exhausted and (n_rows is None or self._buffered < n_rows):
            try:
                batch = self._reader.read_next_batch()
            except StopIteration:
                self._exhausted = True
                break
            if batch.num_rows:
                self._batches.append(batch)
                self._buffered += batch.num_rows
                self._table = None

    def _as_table(self):
        if self._table is None:
            import pyarrow as pa

            self._table = pa.Table.from_batches(self._batches, schema=self._schema)
        return self._table

    def _rows(self, stop):
        if stop <= self._offset:
            return []
        table = intervals_to_durations(
            self._as_table().slice(self._offset, stop - self._offset)
        )
        self._offset = stop
        return list(zip(*(column.to_pylist() for column in table.columns)))

    def fetchone(self):
        rows = self.fetchmany(1)
        return rows[0] if rows else None

    def fetchmany(self, size=1):
        self._read_until(self._offset + size)
        return self._rows(min(self._offset + size, self._buffered))

    def fetchall(self):
        self._read_until(None)
        return self._rows(self._buffered)

    def fetch_arrow_table(self):
        self._read_until(None)
        return self._as_table()

    def close(self):
        if self._reader is not None:
            self._reader.close()
            self._reader = None
        self._cursor.close()
