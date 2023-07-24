"""
nox --session jupysql-integration
"""
from pathlib import Path
from os import environ

import nox


# list non-setup sessions here
nox.options.sessions = ["test_postgres"]

CONDA_PREFIX = environ.get("CONDA_PREFIX")

if CONDA_PREFIX:
    nox.options.envdir = str(Path(CONDA_PREFIX).parent)
else:
    print("CONDA_PREFIX not found, creating envs in default location...")


DEV_ENV_NAME = "jupysql-integration"


INTEGRATION_CONDA_DEPENDENCIES = [
    "pyarrow",
    "psycopg2",
    "pymysql",
    "oracledb",
    "pip",
]

INTEGRATION_PIP_DEPENDENCIES = [
    "dockerctx",
    "pgspecial==2.0.1",
    "pyodbc==4.0.34",
]


def _install(session, integration=False):
    session.install("--editable", ".[dev]")

    if integration:
        session.install(*INTEGRATION_PIP_DEPENDENCIES)
        session.conda_install(
            "--channel", "conda-forge", *INTEGRATION_CONDA_DEPENDENCIES
        )


@nox.session(venv_backend="conda", name=DEV_ENV_NAME)
def setup(session):
    print("Installing requirements...")
    _install(session, integration=False)


@nox.session(venv_backend="conda")
def test_unit(session):
    """Run unit tests (SQLAlchemy 2.x)"""
    _install(session, integration=False)

    # TODO: check sqlalchemy version

    session.run(
        "pytest",
        "src/tests/",
        "--ignore src/tests/integration",
        "--ignore src/tests/test_ggplot.py",
        "--ignore src/tests/test_magic_plot.py",
    )


@nox.session(venv_backend="conda")
def test_unit(session):
    """Run unit tests (SQLAlchemy 1.x)"""
    _install(session, integration=False)
    session.install("sqlalchemy<2")

    # TODO: check sqlalchemy version


@nox.session(venv_backend="conda")
def test_snowflake(session):
    """
    Run snowflake tests (NOTE: the sqlalchemy-snowflake driver only works with
    SQLAlchemy 1.x)
    """
    _install(session, integration=False)
    session.install("snowflake-sqlalchemy")


@nox.session(venv_backend="conda")
def test_postgres(session):
    """Run integration tests (to check compatibility with databases)"""
    _install(session, integration=True)
    session.run(
        "pytest",
        "src/tests/integration/test_generic_db_operations.py",
        "-k",
        "mysql",
    )
