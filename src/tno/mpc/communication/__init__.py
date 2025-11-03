"""
Root imports for the tno.mpc.communication package.
"""

# Explicit re-export of all functionalities, such that they can be imported properly. Following
# https://www.python.org/dev/peps/pep-0484/#stub-files and
# https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-no-implicit-reexport
from tno.mpc.communication.communicators import Communicator as Communicator
from tno.mpc.communication.communicators import HttpCommunicator as HttpCommunicator
from tno.mpc.communication.communicators import HttpConnection as HttpConnection
from tno.mpc.communication.communicators import MockCommunicator as MockCommunicator
from tno.mpc.communication.communicators import MockConnection as MockConnection
from tno.mpc.communication.exceptions import AnnotationError as AnnotationError
from tno.mpc.communication.exceptions import CommunicationError as CommunicationError
from tno.mpc.communication.exceptions import OptionalImportError as OptionalImportError
from tno.mpc.communication.exceptions import RepetitionError as RepetitionError
from tno.mpc.communication.packers import DefaultPacker as DefaultPacker
from tno.mpc.communication.packers import Packer as Packer
from tno.mpc.communication.packers.serialization import Serializer as Serializer
from tno.mpc.communication.packers.serialization import (
    SupportsSerialization as SupportsSerialization,
)
from tno.mpc.communication.pool import Pool as Pool

__version__ = "5.0.4"


# Register all default (de)serializers
Serializer.clear_serialization_logic(reload_defaults=True)
