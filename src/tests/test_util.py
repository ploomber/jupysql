from datetime import datetime
from IPython.core.error import UsageError
import pytest
from sql import util
import json

ERROR_MESSAGE = "Table cannot be None"
EXPECTED_STORE_SUGGESTIONS = (
    "but there is a stored query.\nDid you miss passing --with {0}?"
)


@pytest.fixture
def check_duplicate_message_factory():
    def _generate_error_message(cmd, args, aliases=None):
        error_message = ""
        duplicates = set([arg for arg in args if args.count(arg) != 1])

        if duplicates:
            error_message += (
                f"Duplicate arguments in %{cmd}. "
                "Please use only one of each of the following: "
                f"{', '.join(sorted(duplicates))}."
            )
            if aliases:
                error_message += " "

        if aliases:
            alias_list = []
            for pair in sorted(aliases):
                print(pair[0], pair[1])
                alias_list.append(f"{f'-{pair[0]}'} or {f'--{pair[1]}'}")
            error_message += (
                f"Duplicate aliases for arguments in %{cmd}. "
                "Please use either one of "
                f"{', '.join(alias_list)}."
            )

        return error_message

    return _generate_error_message


@pytest.mark.parametrize(
    "store_table, query",
    [
        pytest.param(
            "a",
            "%sqlcmd columns --table {}",
            marks=pytest.mark.xfail(reason="this is not working yet, see #658"),
        ),
        pytest.param(
            "bbb",
            "%sqlcmd profile --table {}",
            marks=pytest.mark.xfail(reason="this is not working yet, see #658"),
        ),
        ("c_c", "%sqlplot histogram --table {} --column x"),
        ("d_d_d", "%sqlplot boxplot --table {} --column x"),
    ],
    ids=[
        "columns",
        "profile",
        "histogram",
        "boxplot",
    ],
)
def test_no_errors_with_stored_query(ip_empty, store_table, query):
    ip_empty.run_cell("%sql duckdb://")

    ip_empty.run_cell(
        """%%sql
CREATE TABLE numbers (
    x FLOAT
);

INSERT INTO numbers (x) VALUES (1), (2), (3);
"""
    )

    ip_empty.run_cell(
        f"""
        %%sql --save {store_table} --no-execute
        SELECT *
        FROM numbers
        """
    )

    out = ip_empty.run_cell(query.format(store_table, store_table))
    assert out.success


@pytest.mark.parametrize(
    "src, ltypes, expected",
    [
        # 1-D flatten
        ([1, 2, 3], list, [1, 2, 3]),
        # 2-D flatten
        ([(1, 2), 3], None, [1, 2, 3]),
        ([(1, 2), 3], tuple, [1, 2, 3]),
        ([[[1, 2], 3]], list, [1, 2, 3]),
        (([[1, 2], 3]), None, [1, 2, 3]),
        (((1, 2), 3), tuple, (1, 2, 3)),
        (((1, 2), 3), None, (1, 2, 3)),
        (([1, 2], 3), None, (1, 2, 3)),
        (([1, 2], 3), list, (1, 2, 3)),
        # 3-D flatten
        (([[1, 2]], 3), list, (1, 2, 3)),
        (([[1, 2]], 3), None, (1, 2, 3)),
    ],
)
def test_flatten(src, ltypes, expected):
    if ltypes:
        assert util.flatten(src, ltypes) == expected
    else:
        assert util.flatten(src) == expected


date_format = "%Y-%m-%d %H:%M:%S"


@pytest.mark.parametrize(
    "rows, columns, expected_json",
    [
        ([(1, 2), (3, 4)], ["x", "y"], [{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
        ([(1,), (3,)], ["x"], [{"x": 1}, {"x": 3}]),
        (
            [
                ("a", datetime.strptime("2021-01-01 00:30:10", date_format)),
                ("b", datetime.strptime("2021-02-01 00:30:10", date_format)),
            ],
            ["id", "datetime"],
            [
                {
                    "datetime": "2021-01-01 00:30:10",
                    "id": "a",
                },
                {
                    "datetime": "2021-02-01 00:30:10",
                    "id": "b",
                },
            ],
        ),
        (
            [(None, "a1", "b1"), (None, "a2", "b2")],
            ["x", "y", "z"],
            [
                {
                    "x": "None",
                    "y": "a1",
                    "z": "b1",
                },
                {
                    "x": "None",
                    "y": "a2",
                    "z": "b2",
                },
            ],
        ),
    ],
)
def test_parse_sql_results_to_json(ip, capsys, rows, columns, expected_json):
    j = util.parse_sql_results_to_json(rows, columns)
    j = json.loads(j)
    with capsys.disabled():
        assert str(j) == str(expected_json)


@pytest.mark.parametrize(
    "string, substrings, expected",
    [
        ["some-string", ["some", "another"], True],
        ["some-string", ["another", "word"], False],
    ],
)
def test_is_sqlalchemy_error(string, substrings, expected):
    result = util.if_substring_exists(string, substrings)
    assert result == expected


@pytest.mark.parametrize(
    "cmd_from, args, aliases",
    [
        # FOR SQL
        #
        # for creator/c
        (
            "sql",
            ["--creator", "--creator"],
            [],
        ),
        (
            "sql",
            ["-c", "-c"],
            [],
        ),
        (
            "sql",
            ["--creator", "-c"],
            [("c", "creator")],
        ),
        # for persist/p
        (
            "sql",
            ["--persist", "--persist"],
            [],
        ),
        (
            "sql",
            ["-p", "-p"],
            [],
        ),
        (
            "sql",
            ["--persist", "-p"],
            [("p", "persist")],
        ),
        # for no-index/n
        (
            "sql",
            ["--persist", "--no-index", "--no-index"],
            [],
        ),
        (
            "sql",
            ["--persist", "-n", "-n"],
            [],
        ),
        (
            "sql",
            ["--persist", "--no-index", "-n"],
            [("n", "no-index")],
        ),
        # for file/f
        (
            "sql",
            ["--file", "--file"],
            [],
        ),
        (
            "sql",
            ["-f", "-f"],
            [],
        ),
        (
            "sql",
            ["--file", "-f"],
            [("f", "file")],
        ),
        # for save/S
        (
            "sql",
            ["--save", "--save"],
            [],
        ),
        (
            "sql",
            ["-S", "-S"],
            [],
        ),
        (
            "sql",
            ["--save", "-S"],
            [("S", "save")],
        ),
        # for alias/A
        (
            "sql",
            ["--alias", "--alias"],
            [],
        ),
        (
            "sql",
            ["-A", "-A"],
            [],
        ),
        (
            "sql",
            ["--alias", "-A"],
            [("A", "alias")],
        ),
        # for connections/l
        (
            "sql",
            ["--connections", "--connections"],
            [],
        ),
        (
            "sql",
            ["-l", "-l"],
            [],
        ),
        (
            "sql",
            ["--connections", "-l"],
            [("l", "connections")],
        ),
        # for close/x
        (
            "sql",
            ["--close", "--close"],
            [],
        ),
        (
            "sql",
            ["-x", "-x"],
            [],
        ),
        (
            "sql",
            ["--close", "-x"],
            [("x", "close")],
        ),
        # for mixed
        (
            "sql",
            ["--creator", "--creator", "-c", "--persist", "--file", "-f", "-c"],
            [("c", "creator"), ("f", "file")],
        ),
        #
        # FOR SQLPLOT
        #
        # for table/t
        (
            "sqlplot",
            ["--table", "--table", "--column"],
            [],
        ),
        (
            "sqlplot",
            ["-t", "-t", "--column"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "-t", "--column"],
            [("t", "table")],
        ),
        # for column/c
        (
            "sqlplot",
            ["--table", "--column", "--column"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "-c", "-c"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "-c"],
            [("c", "column")],
        ),
        # for bins/b
        (
            "sqlplot",
            ["--table", "--column", "--bins", "--bins"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "-b", "-b"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "--bins", "-b"],
            [("b", "bins")],
        ),
        # for breaks/B
        (
            "sqlplot",
            ["--table", "--column", "--breaks", "--breaks"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "-B", "-B"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "--breaks", "-B"],
            [("B", "breaks")],
        ),
        # for binwidth/W
        (
            "sqlplot",
            ["--table", "--column", "--binwidth", "--binwidth"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "-W", "-W"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "--binwidth", "-W"],
            [("W", "binwidth")],
        ),
        # for orient/o
        (
            "sqlplot",
            ["--table", "--column", "--orient", "--orient"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "-o", "-o"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "--orient", "-o"],
            [("o", "orient")],
        ),
        # for show-numbers/S
        (
            "sqlplot",
            ["--table", "--column", "--show-numbers", "--show-numbers"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "-S", "-S"],
            [],
        ),
        (
            "sqlplot",
            ["--table", "--column", "--show-numbers", "-S"],
            [("S", "show-numbers")],
        ),
        # for mixed
        (
            "sqlplot",
            [
                "--table",
                "--column",
                "--column",
                "-w",
                "--with",
                "--show-numbers",
                "--show-numbers",
                "--binwidth",
                "--orient",
                "-o",
                "--breaks",
                "-B",
            ],
            [("o", "orient"), ("B", "breaks")],
        ),
        #
        # FOR SQLCMD
        #
        # for schema/s
        (
            "sqlcmd",
            ["--schema", "--schema"],
            [],
        ),
        (
            "sqlcmd",
            ["-s", "-s"],
            [],
        ),
        (
            "sqlcmd",
            ["--schema", "-s"],
            [("s", "schema")],
        ),
        # for table/t
        (
            "sqlcmd",
            ["--table", "--table"],
            [],
        ),
        (
            "sqlcmd",
            ["-t", "-t"],
            [],
        ),
        (
            "sqlcmd",
            ["--table", "-t"],
            [("t", "table")],
        ),
        # for mixed
        (
            "sqlcmd",
            ["--table", "-t", "-s", "-s", "--schema"],
            [("t", "table"), ("s", "schema")],
        ),
    ],
)
def test_check_duplicate_arguments_raises_usageerror(
    check_duplicate_message_factory,
    cmd_from,
    args,
    aliases,
):
    with pytest.raises(UsageError) as excinfo:
        util.check_duplicate_arguments(cmd_from, args)
    assert check_duplicate_message_factory(cmd_from, args, aliases) in str(
        excinfo.value
    )


@pytest.mark.parametrize(
    "cmd_from, args",
    [
        (["--creator"], "sql"),
        (["-c"], "sql"),
        (["--persist"], "sql"),
        (["-p"], "sql"),
        (["--persist", "--no-index"], "sql"),
        (["--persist", "-n"], "sql"),
        (["--file"], "sql"),
        (["-f"], "sql"),
        (["--save"], "sql"),
        (["-S"], "sql"),
        (["--alias"], "sql"),
        (["-A"], "sql"),
        (["--connections"], "sql"),
        (["-l"], "sql"),
        (["--close"], "sql"),
        (["-x"], "sql"),
        (["--table", "--column"], "sqlplot"),
        (["--table", "-c"], "sqlplot"),
        (["-t", "--column"], "sqlplot"),
        (["--table", "--column", "--breaks"], "sqlplot"),
        (["--table", "--column", "-B"], "sqlplot"),
        (["--table", "--column", "--bins"], "sqlplot"),
        (["--table", "--column", "-b"], "sqlplot"),
        (["--table", "--column", "--binwidth"], "sqlplot"),
        (["--table", "--column", "-W"], "sqlplot"),
        (["--table", "--column", "--orient"], "sqlplot"),
        (["--table", "--column", "-o"], "sqlplot"),
        (["--table", "--column", "--show-numbers"], "sqlplot"),
        (["--table", "--column", "-S"], "sqlplot"),
        (["--table"], "sqlcmd"),
        (["-t"], "sqlcmd"),
        (["--table", "--schema"], "sqlcmd"),
        (["--table", "-s"], "sqlcmd"),
    ],
)
def test_check_duplicate_arguments_does_not_raise_usageerror(cmd_from, args):
    assert util.check_duplicate_arguments(cmd_from, args)
