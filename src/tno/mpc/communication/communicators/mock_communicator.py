"""
This module contains a mock client and communicator for testing purposes.
"""

from __future__ import annotations

import sys

from tno.mpc.communication.communicators.communicator import Communicator

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class MockConnection:
    """
    Mock Connection.

    Simply keeps a reference to the remote Communicator instance to be able to
    directly call its receive_handler.
    """

    def __init__(self, remote: MockCommunicator):
        """
        Initialise the mock client.

        Each client must have a reference to the communicator of that client.
        E.g. If party A adds party B to its pool, it must provide the
        communicator of Party B as input.

        :param remote: The communicator of that party.
        """
        self.identifier = remote.identifier
        self.communicator = remote

    def __str__(self) -> str:
        """
        String representation of Self.
        """
        return f"MockConnection(remote={self.communicator})"


class MockCommunicator(Communicator[MockConnection]):
    """
    A mock communicator for testing applications. All the pools must be able to
    reference each other's communicators, i.e. be running in the same python process.
    """

    def __init__(self, identifier: str):
        """
        Initialise the mock communicator

        :param identifier: the unique identifier of the communicator
        """
        super().__init__()
        self.identifier = identifier

        self._clients: dict[str, MockConnection] = {}

    @override
    async def _initialize(self) -> None:
        pass

    @override
    async def _send(self, recipient: MockConnection, packet: bytes) -> None:
        """
        'Sends' a packet to another pool, by directly calling the receive
        function on the remote communicator.

        :param recipient: the recipient of the message
        :param packet: the message
        """
        await recipient.communicator.process_packet(self.identifier, packet)

    @override
    async def _shutdown(self) -> None:
        pass

    async def process_packet(self, sender_id: str, packet: bytes) -> None:
        """
        'Receive' a packet from a remote peer.

        :param packet: the message
        :param sender_id: the sender identifier
        """
        await self.receive_handler(sender_id, packet)  # pylint: disable=not-callable

    def __str__(self) -> str:
        """
        String representation of Self.
        """
        return f"MockCommunicator(identifier={self.identifier})"
