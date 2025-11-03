"""
Module for testing the functionality built into the base (abstract) Communicator class.

This functionality is mainly the state machine that the Communicator class adheres to.
"""

import sys

import pytest

from tno.mpc.communication import Communicator
from tno.mpc.communication.communicators.communicator import IllegalStateAction

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class DummyConnection:
    """
    Dummy Connection.
    """


class DummyCommunicator(Communicator[DummyConnection]):
    """
    Dummy implementation of Communicator for testing the base functionality.
    """

    @override
    async def _initialize(self) -> None:
        pass

    @override
    async def _send(self, recipient: DummyConnection, packet: bytes) -> None:
        pass

    @override
    async def _shutdown(self) -> None:
        pass


@pytest.fixture(name="communicator")
def fixture_communicator() -> DummyCommunicator:
    """
    Fixture returning an instantiated DummyCommunicator.

    :returns: An instantiated DummyCommunicator.
    """
    return DummyCommunicator()


@pytest.mark.asyncio
async def test_cannot_send_if_not_initialized(communicator: DummyCommunicator) -> None:
    """
    Assert error is raised when send is called on an uninitialized communicator.

    :param communicator: Initialized dummy communicator.
    """
    with pytest.raises(IllegalStateAction):
        await communicator.send("recipient", b"message")


@pytest.mark.asyncio
async def test_cannot_shutdown_if_not_initialized(
    communicator: DummyCommunicator,
) -> None:
    """
    Assert error is raised when shutdown is called on an uninitialized communicator.

    :param communicator: Initialized dummy communicator.
    """
    with pytest.raises(IllegalStateAction):
        await communicator.shutdown()


@pytest.mark.asyncio
async def test_cannot_initialize_twice(communicator: DummyCommunicator) -> None:
    """
    Assert error is raised when communicator is initialized twice.

    :param communicator: Initialized dummy communicator.
    """
    with pytest.raises(IllegalStateAction):
        await communicator.initialize()
        await communicator.initialize()


@pytest.mark.asyncio
async def test_cannot_add_connection_if_initialized(
    communicator: DummyCommunicator,
) -> None:
    """
    Assert error is raised when a connection is added after the communicator is initialized.

    :param communicator: Initialized dummy communicator.
    """
    await communicator.initialize()

    with pytest.raises(IllegalStateAction):
        communicator.add_connection("same_name", DummyConnection())


@pytest.mark.asyncio
async def test_cannot_send_to_unknown_connection(
    communicator: DummyCommunicator,
) -> None:
    """
    Assert error is raised when a message is sent to an unknown connection.

    :param communicator: Initialized dummy communicator.
    """
    await communicator.initialize()

    with pytest.raises(KeyError):
        await communicator.send("unknown", b"message")


@pytest.mark.asyncio
async def test_cannot_add_connection_with_existing_name(
    communicator: DummyCommunicator,
) -> None:
    """
    Assert error is raised when adding a connection of the same name twice.

    :param communicator: Initialized dummy communicator.
    """
    with pytest.raises(KeyError):
        communicator.add_connection("same_name", DummyConnection())
        communicator.add_connection("same_name", DummyConnection())
