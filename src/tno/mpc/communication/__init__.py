"""
Communication library for sending arbitrary Python data types over HTTP(S).
"""

# Explicit re-export of all functionalities, such that they can be imported properly. Following
# https://www.python.org/dev/peps/pep-0484/#stub-files and
# https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-no-implicit-reexport
from tno.mpc.communication.exceptions import AnnotationError as AnnotationError
from tno.mpc.communication.exceptions import OptionalImportError as OptionalImportError
from tno.mpc.communication.exceptions import RepetitionError as RepetitionError
from tno.mpc.communication.pool import Pool as Pool
from tno.mpc.communication.serialization import Serialization as Serialization
from tno.mpc.communication.serialization import (
    SupportsSerialization as SupportsSerialization,
)

__version__ = "4.8.1"


# Register all default (de)serializers
Serialization.clear_serialization_logic(reload_defaults=True)
