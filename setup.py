import os
from io import open
import re
import ast

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, "README.md"), encoding="utf-8").read()

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("src/sql/__init__.py", "rb") as f:
    VERSION = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

install_requires = [
    # 3.18.0 raises ValueError when rendering a table with no columns
    "prettytable>=3.12.0,<3.18.0",
    # IPython dropped support for Python 3.8
    "ipython<=8.12.0; python_version <= '3.8'",
    "sqlalchemy",
    "sqlparse",
    "ipython-genutils>=0.1.0",
    "jinja2",
    "sqlglot>=11.3.7",
    'importlib-metadata;python_version<"3.8"',
    # we removed the share notebook button in this version
    "jupysql-plugin>=0.4.2",
    "ploomber-core>=0.2.7",
]

DEV = [
    "flake8",
    "pytest",
    # pandas 2.2+ dropped support for SQLAlchemy 1.x; the SQLAlchemy 1.x
    # session in noxfile.py downgrades pandas
    "pandas<3",
    "polars==0.17.2",  # 04/18/23 this breaks our CI
    # matplotlib 3.7 (pinned for the image baselines) is not compatible with NumPy 2
    "numpy<2",
    # pyarrow 26+ requires NumPy 2
    "pyarrow<26",
    "invoke",
    "pkgmt",
    "twine",
    # tests
    "duckdb<1.1.0",
    "duckdb-engine",
    "pyodbc",
    # sql.plot module tests
    "matplotlib==3.7.2",
    "black==25.1.0",
    # for %%sql --interact
    "ipywidgets",
    # for running tests for %sqlcmd explore --table
    "js2py",
    # for monitoring access to files
    "psutil",
    # for running tests for %sqlcmd connect
    "jupyter-server",
]

# dependencies for running integration tests
INTEGRATION = [
    "dockerctx",
    "pyarrow",
    "psycopg2-binary",
    "pymysql",
    "pgspecial==2.0.1",
    "pyodbc",
    "snowflake-sqlalchemy",
    "oracledb",
    "sqlalchemy-pytds",
    "python-tds",
    # redshift
    "redshift-connector",
    "sqlalchemy-redshift",
    "clickhouse-sqlalchemy",
    # following two dependencies required for spark
    "pyspark",
    "grpcio-status",
]

setup(
    name="jupysql",
    version=VERSION,
    description="Better SQL in Jupyter",
    long_description=README,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Database",
        "Topic :: Database :: Front-Ends",
        "Programming Language :: Python :: 3",
    ],
    keywords="database ipython postgresql mysql duckdb",
    author="Ploomber",
    author_email="contact@ploomber.io",
    url="https://github.com/ploomber/jupysql",
    project_urls={
        "Source": "https://github.com/ploomber/jupysql",
    },
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        "dev": DEV,
        "integration": DEV + INTEGRATION,
    },
)
