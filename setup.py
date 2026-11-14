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
    "prettytable>=3.12.0",
    "sqlalchemy>=2",
    "ipython",
    "sqlparse",
    "ipython-genutils>=0.1.0",
    "jinja2",
    "sqlglot>=11.3.7",
    # we removed the share notebook button in this version
    "jupysql-plugin>=0.4.2",
    "ploomber-core>=0.2.7",
]

DEV = [
    "flake8",
    "pytest",
    "pandas==3.1.1",
    "numpy==2.4.6",
    "pyarrow==26.0.1",
    "polars==2.1.0",
    "invoke",
    "pkgmt",
    "twine",
    # tests
    "duckdb==2.0.0",
    "duckdb-engine",
    "pyodbc",
    # sql.plot module tests; pinned because the tests compare against baseline images
    "matplotlib==3.11.2",
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
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.11",
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
