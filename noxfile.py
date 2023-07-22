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
    "snowflake-sqlalchemy",
    "oracledb",
    "pip",
]

INTEGRATION_PIP_DEPENDENCIES = [
    "dockerctx",
    "pgspecial==2.0.1",
    "pyodbc==4.0.34",
]


def _install(session, api=False, doc=False, postgres=False):
    session.install("--editable", ".[dev]")
    session.install(*INTEGRATION_PIP_DEPENDENCIES)
    session.conda_install("--channel", "conda-forge", *INTEGRATION_CONDA_DEPENDENCIES)

    # session.run(
    #     "python",
    #     "-m",
    #     "bash_kernel.install",
    #     "--sys-prefix",
    #     "--conda-activate",
    #     DEV_ENV_NAME,
    # )


@nox.session(venv_backend="conda", name=DEV_ENV_NAME)
def setup(session):
    print("Installing requirements...")
    _install(session)


@nox.session(venv_backend="conda")
def test_unit(session):
    pass


@nox.session(venv_backend="conda")
def test_snowflake(session):
    pass


@nox.session(venv_backend="conda")
def test_postgres(session):
    _install(session)
    session.run(
        "pytest",
        "src/tests/integration/test_generic_db_operations.py",
        "-k",
        "mysql",
    )
