from sql import inspect
from sql.util import sanitize_identifier
from sql.cmd.cmd_utils import CmdParser


def execute_columns_command(others):
    """
    Execution logic for the columns command

    """
    parser = CmdParser()

    parser.add_argument("-t", "--table", type=str, help="Table name", required=True)
    parser.add_argument("-s", "--schema", type=str, help="Schema name", required=False)

    args = parser.parse_args(others)
    return inspect.get_columns(name=sanitize_identifier(args.table), schema=args.schema)
