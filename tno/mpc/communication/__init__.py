"""
Communication library for sending arbitrary Python data types over HTTP(S).
"""

# Explicit re-export of all functionalities, such that they can be imported properly. Following
# https://www.python.org/dev/peps/pep-0484/#stub-files and
# https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-no-implicit-reexport
from tno.mpc.communication.pool import Pool as Pool

__version__ = "1.0.4"


def init_pool() -> Pool:
    """
    Initializes a new Pool object.

    :return: new Pool object.
    """
    return Pool()
