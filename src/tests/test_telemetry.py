from pathlib import Path
from unittest.mock import ANY, Mock
import pytest
import urllib.request
import duckdb
from sql.telemetry import telemetry


# Ref: https://pytest.org/en/7.2.x/how-to/tmp_path.html#
# Utilize tmp directory to store downloaded csv


@pytest.fixture
def simple_file_path_iris(tmpdir):
    file_path_str = str(tmpdir.join("iris.csv"))

    if not Path(file_path_str).is_file():
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/plotly/datasets/master/iris-data.csv",
            file_path_str,
        )

    yield file_path_str


@pytest.fixture
def simple_file_path_penguins(tmpdir):
    file_path_str = str(tmpdir.join("penguins.csv"))

    if not Path(file_path_str).is_file():
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com"
            "/mwaskom/seaborn-data/master/penguins.csv",
            file_path_str,
        )

    yield file_path_str


@pytest.fixture
def simple_db_conn():
    conn = duckdb.connect(database=":memory:")
    return conn


@pytest.fixture
def mock_log_api(monkeypatch):
    mock_log_api = Mock()
    monkeypatch.setattr(telemetry, "log_api", mock_log_api)
    yield mock_log_api


def test_boxplot_telemetry_execution(mock_log_api, ip, simple_file_path_penguins):
    ip.run_cell("%sql duckdb://")
    ip.run_cell(
        "%sqlplot boxplot --table "
        + simple_file_path_penguins
        + " --column body_mass_g"
    )

    mock_log_api.assert_called_with(
        action="jupysql-boxplot-success",
        total_runtime=ANY,
        metadata={"argv": ANY, "dialect_meta": "duckdb"},
    )


def test_histogram_telemetry_execution(mock_log_api, ip, simple_file_path_penguins):
    ip.run_cell("%sql duckdb://")
    ip.run_cell(
        "%sql --save not_empty_data --no-execute \
        SELECT * FROM read_csv_auto('"
        + simple_file_path_penguins
        + "') WHERE body_mass_g IS NOT NULL"
    )
    ip.run_cell(
        "%sqlplot histogram --table not_empty_data\
         --column body_mass_g --with not_empty_data"
    )

    mock_log_api.assert_called_with(
        action="jupysql-histogram-success",
        total_runtime=ANY,
        metadata={"argv": ANY, "dialect_meta": "duckdb"},
    )


def test_data_frame_telemetry_execution(mock_log_api, ip, simple_file_path_iris):
    # Simulate the cell query & get the DataFrame
    ip.run_cell("%sql duckdb://")
    ip.run_cell(
        "result = %sql SELECT * FROM read_csv_auto('" + simple_file_path_iris + "')"
    )
    ip.run_cell("result.DataFrame()")
    mock_log_api.assert_called_with(
        action="jupysql-data-frame-success", total_runtime=ANY, metadata=ANY
    )


def test_sqlrender_telemetry_execution(mock_log_api, ip, simple_file_path_iris):
    # Simulate the sqlrender query
    ip.run_cell("%sql duckdb://")
    ip.run_cell(
        "%sql --save class_setosa --no-execute \
            SELECT * FROM read_csv_auto('"
        + simple_file_path_iris
        + "' WHERE class='Iris-setosa'"
    )
    ip.run_cell("%sqlrender class_setosa")

    mock_log_api.assert_called_with(
        action="jupysql-sqlrender-success", total_runtime=ANY, metadata=ANY
    )


def test_execute_telemetry_execution(mock_log_api, ip):
    ip.run_cell("%sql duckdb://")

    mock_log_api.assert_called_with(
        action="jupysql-execute-success", total_runtime=ANY, metadata=ANY
    )


def test_sql_execute_send_dialect_meta(mock_log_api, ip):
    ip.run_cell("%sql duckdb://")

    mock_log_api.assert_called_with(
        action="jupysql-execute-success",
        total_runtime=ANY,
        metadata={"argv": ANY, "dialect_meta": "duckdb"},
    )
