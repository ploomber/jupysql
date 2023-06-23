from sql.widgets import TableWidget
from IPython.display import display

from sql.cmd.cmd_utils import CmdParser


def execute_expolore_command(others):
    """
    Execution logic for the explore command

    """
    parser = CmdParser()
    parser.add_argument("-t", "--table", type=str, help="Table name", required=True)
    args = parser.parse_args(others)

    table_widget = TableWidget(args.table)
    display(table_widget)
