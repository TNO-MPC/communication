"""
Module that defines the communication layer
"""

from tno.mpc.communication.communicators.communicator import (
    Communicator as Communicator,
)
from tno.mpc.communication.communicators.http_communicator import (
    HttpCommunicator as HttpCommunicator,
)
from tno.mpc.communication.communicators.http_communicator import (
    HttpConnection as HttpConnection,
)
from tno.mpc.communication.communicators.mock_communicator import (
    MockCommunicator as MockCommunicator,
)
from tno.mpc.communication.communicators.mock_communicator import (
    MockConnection as MockConnection,
)
