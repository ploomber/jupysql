from sql import inspect
from sql.cmd.cmd_utils import CmdParser


def execute_tables_command(others):
    """
    Execution logic for the tables command

    """
    parser = CmdParser()

    parser.add_argument("-s", "--schema", type=str, help="Schema name", required=False)

    args = parser.parse_args(others)

    return inspect.get_table_names(schema=args.schema)
