import pandas as pd
import pytest
from sqlalchemy import create_engine

# TODO: move postgreSQLConfig to individual file, shared with ci-integration-db
databaseConfig = {
    # Database Config
    "db_name": "db",
    # MySQL Service Config
    "endpoint": "localhost:33306",
    "user": "ploomber_app",
    "password": "ploomber_app_password",
    "root_password": "ploomber_app_root_password",
}


# SQLAlchmey URL: https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls
def get_database_url():
    return "mysql+pymysql://{}:{}@{}/{}".format(
        databaseConfig["user"],
        databaseConfig["password"],
        databaseConfig["endpoint"],
        databaseConfig["db_name"],
    )


@pytest.fixture(scope="session", autouse=True)
def setup_mySQL():
    engine = create_engine(get_database_url())
    # Load taxi_data
    taxi_data(engine)
    yield engine
    engine.dispose()


def taxi_data(engine):
    table_name = "taxi"
    df = pd.DataFrame(
        {"taxi_driver_name": ["Eric Ken", "John Smith", "Kevin Kelly"] * 15}
    )
    df.to_sql(name=table_name, con=engine, chunksize=100_000, if_exists="replace")


@pytest.fixture
def ip_with_db(ip):
    # Disconnect build-in sqlite connection
    ip.run_cell("%sql --close sqlite://")
    # Connect
    ip.run_cell("%sql " + get_database_url() + " --alias mySQLTest")
    yield ip
    # Disconnect
    ip.run_cell("%sql -x mySQLTest")


# Query
def test_query_count(ip_with_db):
    out = ip_with_db.run_line_magic("sql", "SELECT * FROM taxi LIMIT 3")
    print("count out: ", len(out))
    assert len(out) == 3


# Create table
def test_create_table_with_indexed_df(ip_with_db):
    ip_with_db.run_cell("results = %sql SELECT * FROM taxi LIMIT 15")
    ip_with_db.run_cell("new_table_from_df = results.DataFrame()")
    ip_with_db.run_cell("%sql --persist sqlite:// new_table_from_df")
    out = ip_with_db.run_cell("%sql SELECT * FROM new_table_from_df")

    assert len(out.result) == 15


# Connection - Connect & Close and List
def get_connection_count(ip_with_db):
    out = ip_with_db.run_line_magic("sql", "-l")
    print("Current connections:", out)
    connections_count = len(out)
    return connections_count


def test_list_connection(ip_with_db):
    assert get_connection_count(ip_with_db) == 1


def test_close_and_connect(ip_with_db):
    # Disconnect
    ip_with_db.run_cell("%sql -x mySQLTest")
    assert get_connection_count(ip_with_db) == 0
    # Connect
    ip_with_db.run_cell("%sql " + get_database_url() + " --alias mySQLTest")
    assert get_connection_count(ip_with_db) == 1
