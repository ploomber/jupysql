from datetime import datetime
from IPython.core.error import UsageError
import pytest
from sql import util
import json
from sql.magic import SqlMagic
from sql.magic_cmd import SqlCmdMagic
from sql.magic_plot import SqlPlotMagic

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


ALLOWED_DUPLICATES = {
    "sql": ["-w", "--with", "--append", "--interact"],
    "sqlplot": ["-w", "--with"],
    "sqlcmd": [],
}

DISALLOWED_ALIASES = {
    "sql": {},
    "sqlplot": {},
    "sqlcmd": {
        "-t": "--table",
        "-s": "--schema",
        "-o": "--output",
    },
}


@pytest.mark.parametrize(
    "magic_execute, cmd_from, args, aliases",
    [
        # FOR SQL
        #
        # for creator/c
        (
            SqlMagic.execute,
            "sql",
            ["--creator", "--creator"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["-c", "-c"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--creator", "-c"],
            [("c", "creator")],
        ),
        # for persist/p
        (
            SqlMagic.execute,
            "sql",
            ["--persist", "--persist"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["-p", "-p"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--persist", "-p"],
            [("p", "persist")],
        ),
        # for no-index/n
        (
            SqlMagic.execute,
            "sql",
            ["--persist", "--no-index", "--no-index"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--persist", "-n", "-n"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--persist", "--no-index", "-n"],
            [("n", "no-index")],
        ),
        # for file/f
        (
            SqlMagic.execute,
            "sql",
            ["--file", "--file"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["-f", "-f"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--file", "-f"],
            [("f", "file")],
        ),
        # for save/S
        (
            SqlMagic.execute,
            "sql",
            ["--save", "--save"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["-S", "-S"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--save", "-S"],
            [("S", "save")],
        ),
        # for alias/A
        (
            SqlMagic.execute,
            "sql",
            ["--alias", "--alias"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["-A", "-A"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--alias", "-A"],
            [("A", "alias")],
        ),
        # for connections/l
        (
            SqlMagic.execute,
            "sql",
            ["--connections", "--connections"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["-l", "-l"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--connections", "-l"],
            [("l", "connections")],
        ),
        # for close/x
        (
            SqlMagic.execute,
            "sql",
            ["--close", "--close"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["-x", "-x"],
            [],
        ),
        (
            SqlMagic.execute,
            "sql",
            ["--close", "-x"],
            [("x", "close")],
        ),
        # for mixed
        (
            SqlMagic.execute,
            "sql",
            ["--creator", "--creator", "-c", "--persist", "--file", "-f", "-c"],
            [("c", "creator"), ("f", "file")],
        ),
        #
        # FOR SQLPLOT
        #
        # for table/t
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--table", "--column"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["-t", "-t", "--column"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "-t", "--column"],
            [("t", "table")],
        ),
        # for column/c
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--column"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "-c", "-c"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "-c"],
            [("c", "column")],
        ),
        # for bins/b
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--bins", "--bins"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "-b", "-b"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--bins", "-b"],
            [("b", "bins")],
        ),
        # for breaks/B
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--breaks", "--breaks"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "-B", "-B"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--breaks", "-B"],
            [("B", "breaks")],
        ),
        # for binwidth/W
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--binwidth", "--binwidth"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "-W", "-W"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--binwidth", "-W"],
            [("W", "binwidth")],
        ),
        # for orient/o
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--orient", "--orient"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "-o", "-o"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--orient", "-o"],
            [("o", "orient")],
        ),
        # for show-numbers/S
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--show-numbers", "--show-numbers"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "-S", "-S"],
            [],
        ),
        (
            SqlPlotMagic.execute,
            "sqlplot",
            ["--table", "--column", "--show-numbers", "-S"],
            [("S", "show-numbers")],
        ),
        # for mixed
        (
            SqlPlotMagic.execute,
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
            [("w", "with"), ("o", "orient"), ("B", "breaks")],
        ),
        #
        # FOR SQLCMD
        #
        # for schema/s
        (
            SqlCmdMagic.execute,
            "sqlcmd",
            ["--schema", "--schema"],
            [],
        ),
        (
            SqlCmdMagic.execute,
            "sqlcmd",
            ["-s", "-s"],
            [],
        ),
        (
            SqlCmdMagic.execute,
            "sqlcmd",
            ["--schema", "-s"],
            [("s", "schema")],
        ),
        # for table/t
        (
            SqlCmdMagic.execute,
            "sqlcmd",
            ["--table", "--table"],
            [],
        ),
        (
            SqlCmdMagic.execute,
            "sqlcmd",
            ["-t", "-t"],
            [],
        ),
        (
            SqlCmdMagic.execute,
            "sqlcmd",
            ["--table", "-t"],
            [("t", "table")],
        ),
        # for mixed
        (
            SqlCmdMagic.execute,
            "sqlcmd",
            ["--table", "-t", "-s", "-s", "--schema"],
            [("t", "table"), ("s", "schema")],
        ),
    ],
)
def test_check_duplicate_arguments_raises_usageerror(
    check_duplicate_message_factory,
    magic_execute,
    cmd_from,
    args,
    aliases,
):
    with pytest.raises(UsageError) as excinfo:
        util.check_duplicate_arguments(
            magic_execute,
            cmd_from,
            args,
            ALLOWED_DUPLICATES[cmd_from],
            DISALLOWED_ALIASES[cmd_from],
        )
    assert check_duplicate_message_factory(cmd_from, args, aliases) in str(
        excinfo.value
    )


@pytest.mark.parametrize(
    "magic_execute, args, cmd_from",
    [
        (SqlMagic.execute, ["--creator"], "sql"),
        (SqlMagic.execute, ["-c"], "sql"),
        (SqlMagic.execute, ["--persist"], "sql"),
        (SqlMagic.execute, ["-p"], "sql"),
        (SqlMagic.execute, ["--persist", "--no-index"], "sql"),
        (SqlMagic.execute, ["--persist", "-n"], "sql"),
        (SqlMagic.execute, ["--file"], "sql"),
        (SqlMagic.execute, ["-f"], "sql"),
        (SqlMagic.execute, ["--save"], "sql"),
        (SqlMagic.execute, ["-S"], "sql"),
        (SqlMagic.execute, ["--alias"], "sql"),
        (SqlMagic.execute, ["-A"], "sql"),
        (SqlMagic.execute, ["--connections"], "sql"),
        (SqlMagic.execute, ["-l"], "sql"),
        (SqlMagic.execute, ["--close"], "sql"),
        (SqlMagic.execute, ["-x"], "sql"),
        (SqlPlotMagic.execute, ["--table", "--column"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "-c"], "sqlplot"),
        (SqlPlotMagic.execute, ["-t", "--column"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "--breaks"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "-B"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "--bins"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "-b"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "--binwidth"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "-W"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "--orient"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "-o"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "--show-numbers"], "sqlplot"),
        (SqlPlotMagic.execute, ["--table", "--column", "-S"], "sqlplot"),
        (SqlCmdMagic.execute, ["--table"], "sqlcmd"),
        (SqlCmdMagic.execute, ["-t"], "sqlcmd"),
        (SqlCmdMagic.execute, ["--table", "--schema"], "sqlcmd"),
        (SqlCmdMagic.execute, ["--table", "-s"], "sqlcmd"),
    ],
)
def test_check_duplicate_arguments_does_not_raise_usageerror(
    magic_execute, args, cmd_from
):
    assert util.check_duplicate_arguments(
        magic_execute, cmd_from, args, ALLOWED_DUPLICATES[cmd_from]
    )
