from IPython.core.magic import (
    Magics,
    line_magic,
    magics_class,
)
from IPython.core.magic_arguments import argument, magic_arguments


try:
    from traitlets.config.configurable import Configurable
except ImportError:
    from IPython.config.configurable import Configurable


from sql import plot
from sql.command import SQLPlotCommand
from sql.connection import Connection


@magics_class
class SqlPlotMagic(Magics, Configurable):
    """%sqlplot magic"""

    @line_magic("sqlplot")
    @magic_arguments()
    @argument("line", default="", nargs="*", type=str, help="Plot name")
    @argument("-t", "--table", type=str, help="Table to use")
    @argument("-c", "--column", type=str, help="Column to use")
    @argument(
        "-b",
        "--bins",
        type=int,
        default=50,
        help="Histogram bins",
    )
    def execute(self, line="", cell="", local_ns={}):
        """
        Plot magic
        """

        cmd = SQLPlotCommand(self, line)

        if cmd.args.line[0] == "box":
            plot.boxplot(table=cmd.args.table, column=cmd.args.column, conn=None)
        else:
            plot.histogram(
                table=cmd.args.table, column=cmd.args.column, bins=cmd.args.bins
            )
