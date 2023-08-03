from sqlglot import parse_one, exp
from sqlglot.errors import ParseError
import re
import json


def extract_tables_from_query(query):
    """
    Function to extract names of tables from
    a syntactically correct query

    Parameters
    ----------
    query : str, user query

    Returns
    -------
    list
        List of tables in the query
        [] if error in parsing the query
    """
    try:
        tables = [table.name for table in parse_one(query).find_all(exp.Table)]
        return tables
    except ParseError:
        # TODO : Instead of returning [] replace with call to
        # error_messages.py::parse_sqlglot_error. Currently this
        # is not possible because of an exception raised in test
        # fixtures. (#546). This function can also be moved to util.py
        # after #545 is resolved.
        return []


def parse_sql_snippet(snippet):
    """Parse the snippet content from the .sql file
    to extract the snippet statement and the
    dependencies.
    """
    metadata = extract_metadata(snippet)
    main_sql = extract_main_sql(snippet)

    return {"with_": metadata, "main_sql": main_sql}


def extract_metadata(snippet):
    """Extract the with_ metadata from the snippet
    contents.
    """
    metadata_pattern = re.compile(r"/\* \{(.*?)\} \*/", re.DOTALL)
    match = metadata_pattern.search(snippet)
    if match:
        metadata_json = match.group(1)
        return json.loads("{" + metadata_json + "}").get("with_")
    return None


def extract_main_sql(snippet):
    """Extract the snippet content from within
    the SNIPPET BEGINS/ENDS markers.
    """
    main_sql_pattern = re.compile(
        r"/\* SNIPPET BEGINS \*/\s*(.*?)\s*/\* SNIPPET ENDS \*/", re.DOTALL
    )
    match = main_sql_pattern.search(snippet)
    if match:
        return match.group(1).strip()
    return None


def write_sql_with_markers(content, dependencies=None):
    """Create and populate a string with the contents of a
    snippet and its dependencies, which will be stored as
    a .sql file.

    Parameters
    ----------
    content : str,
        snippet content

    dependencies : dict, DEFAULT None
        A dictionary with
        key : snippet name
        value : content of the snippet

    Returns
    ----------
    marked_sql : str
        Content to be stored as a .sql file
    """
    metadata = ""
    dep = ""
    if dependencies:
        metadata = json.dumps({"with_": list(dependencies.keys())})
        dep = _generate_dependencies_parser(dependencies)

    marked_sql = f"""
/* This SQL file was produced by JupySQL, do not edit directly.
Edit the notebook where this snippet was defined */
/* {metadata} */

{dep}
/* SNIPPET BEGINS */
{content}
/* SNIPPET ENDS */
"""
    return marked_sql


def _generate_dependencies_parser(dependencies):
    """Create a string with contents of different
    snippet dependencies appended together.

    Parameters
    ----------
    dependencies : dict,
        A dictionary with
        key : snippet name
        value : content of the snippet

    Returns
    ----------
    dep_string : str
        A string with different snippet dependencies
        stiched together
    """
    dep_parts = []
    for key, value in dependencies.items():
        dep_parts.append(f"{key} as ({value}\n)")

    # Prefix the 'with' keyword, and join dependencies with comma and newline.
    dep_string = "with " + ",".join(dep_parts) + "," if dep_parts else ""
    return dep_string
