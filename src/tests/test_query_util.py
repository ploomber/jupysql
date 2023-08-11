import pytest
from sql import query_util
import json


@pytest.mark.parametrize(
    "input_dependencies, expected_output",
    [
        ({}, ""),
        (
            {"snippet1": "SELECT column1 FROM table1;"},
            "with snippet1 as (SELECT column1 FROM table1;\n),",
        ),
        (
            {
                "snippet1": "SELECT column1 FROM table1;",
                "snippet2": "SELECT column2 FROM table2;",
            },
            (
                "with snippet1 as (SELECT column1 FROM table1;\n),"
                "snippet2 as (SELECT column2 FROM table2;\n),"
            ),
        ),
    ],
)
def test_generate_dependencies_parser(input_dependencies, expected_output):
    print(query_util._generate_dependencies_parser(input_dependencies))
    assert (
        query_util._generate_dependencies_parser(input_dependencies) == expected_output
    )


@pytest.mark.parametrize(
    "content, dependencies, expected_metadata, expected_dep",
    [
        ("SELECT * FROM table_name;", None, "", ""),
        (
            "SELECT * FROM table_name;",
            {
                "snippet1": "SELECT column1 FROM table1;",
                "snippet2": "SELECT column2 FROM table2;",
            },
            json.dumps({"with_": ["snippet1", "snippet2"]}),
            query_util._generate_dependencies_parser(
                {
                    "snippet1": "SELECT column1 FROM table1;",
                    "snippet2": "SELECT column2 FROM table2;",
                }
            ),
        ),
    ],
)
def test_write_sql_with_markers(content, dependencies, expected_metadata, expected_dep):
    expected_sql = f"""
/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/* {expected_metadata} */

{expected_dep}
/* SNIPPET BEGINS */
{content}
/* SNIPPET ENDS */
"""

    assert query_util.write_sql_with_markers(content, dependencies) == expected_sql


@pytest.mark.parametrize(
    "input_snippet, expected_output",
    [
        (
            """/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/* {"with_": ["citizen", "citizen_another"]} */

with citizen as (
select * from people where country = 'usa'
),citizen_another as (
select * from citizen where number = 82
),

/* SNIPPET BEGINS */
select * from citizen_another where name == 'robert'
/* SNIPPET ENDS */""",
            "select * from citizen_another where name == 'robert'",
        ),
        (
            """/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/*  */
/* SNIPPET BEGINS */
select * from people
/* SNIPPET ENDS */""",
            "select * from people",
        ),
        ("SELECT * FROM table_name;", None),
    ],
)
def test_extract_main_sql(input_snippet, expected_output):
    assert query_util.extract_main_sql(input_snippet) == expected_output


@pytest.mark.parametrize(
    "input_snippet, expected_output",
    [
        (
            """/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/* {"with_": ["citizen", "citizen_another"]} */

with citizen as (
select * from people where country = 'usa'
),citizen_another as (
select * from citizen where number = 82
),

/* SNIPPET BEGINS */
select * from citizen_another where name == 'robert'
/* SNIPPET ENDS */""",
            ["citizen", "citizen_another"],
        ),
        (
            """/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/*  */
/* SNIPPET BEGINS */
select * from people
/* SNIPPET ENDS */""",
            None,
        ),
    ],
)
def test_extract_metadata(input_snippet, expected_output):
    assert query_util.extract_metadata(input_snippet) == expected_output


@pytest.mark.parametrize(
    "input_snippet, expected_output",
    [
        (
            """/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/* {"with_": ["citizen", "citizen_another"]} */

with citizen as (
select * from people where country = 'usa'
),citizen_another as (
select * from citizen where number = 82
),

/* SNIPPET BEGINS */
select * from citizen_another where name == 'robert'
/* SNIPPET ENDS */""",
            {
                "with_": ["citizen", "citizen_another"],
                "main_sql": "select * from citizen_another where name == 'robert'",
            },
        ),
        (
            """/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/*  */
/* SNIPPET BEGINS */
select * from people
/* SNIPPET ENDS */""",
            {"with_": None, "main_sql": "select * from people"},
        ),
    ],
)
def test_parse_sql_snippet(input_snippet, expected_output):
    assert query_util.parse_sql_snippet(input_snippet) == expected_output
