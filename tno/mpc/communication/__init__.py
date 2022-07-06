"""
Communication library for sending arbitrary Python data types over HTTP(S).
"""

# Explicit re-export of all functionalities, such that they can be imported properly. Following
# https://www.python.org/dev/peps/pep-0484/#stub-files and
# https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-no-implicit-reexport
from tno.mpc.communication.pool import Pool as Pool
from tno.mpc.communication.serialization import AnnotationError as AnnotationError
from tno.mpc.communication.serialization import RepetitionError as RepetitionError
from tno.mpc.communication.serialization import Serialization as Serialization
from tno.mpc.communication.serialization import (
    SupportsSerialization as SupportsSerialization,
)

__version__ = "3.4.1"


def init_pool() -> Pool:
    """
    Initializes a new Pool object.

    :return: new Pool object.
    """
    return Pool()
