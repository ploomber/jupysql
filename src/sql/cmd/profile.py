from sql import inspect
from sql.cmd.cmd_utils import CmdParser


def execute_profile_command(others):
    """
    Execution logic for the profile command

    """
    parser = CmdParser()
    parser.add_argument("-t", "--table", type=str, help="Table name", required=True)

    parser.add_argument("-s", "--schema", type=str, help="Schema name", required=False)

    parser.add_argument(
        "-o", "--output", type=str, help="Store report location", required=False
    )

    args = parser.parse_args(others)

    report = inspect.get_table_statistics(schema=args.schema, name=args.table)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report._repr_html_())

    return report
