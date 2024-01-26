from traitlets import TraitError, TraitType
from sql import display
import warnings

VALUE_WARNING = (
    "Please use a valid option: \"warn\", \"enabled\", or \"disabled\". \n"
    "For more information, see the docs: https://jupysql.ploomber.io/en/latest/api/configuration.html"
)

class Parameters(TraitType):

    def __init__(self, **kwargs):
        super(Parameters, self).__init__(**kwargs)

    def validate(self, obj, value):
        if isinstance(value, bool):
            if value == True:
                warnings.warn(f"named_parameters: boolean values are now deprecated. Value {value} will be treated as \"enabled\". \n{VALUE_WARNING}", FutureWarning)
                return "enabled"
            else:
                warnings.warn(f"named_parameters: boolean values are now deprecated. Value {value} will be treated as \"warn\" (default). \n{VALUE_WARNING}", FutureWarning)
                return "warn"
        elif isinstance(value, str):
            if not value:
                display.message(f"named_parameters: Value \"\" will be treated as \"warn\" (default)")
                return "warn"

            value = value.lower()
            if value not in ("warn", "enabled", "disabled"):
                raise TraitError(
                    f"{value} is not a valid option for named_parameters. "
                    f"Valid options are: \"warn\", \"enabled\", or \"disabled\"."
                )

            return value

        else:
            raise TraitError(
                    f"{value} is not a valid option for named_parameters. "
                    f"Valid options are: \"warn\", \"enabled\", or \"disabled\"."
                )