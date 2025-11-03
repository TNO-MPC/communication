"""
Tests for the Pool interface testing whether the Pool correctly transitions the state machine of the Communicator.
"""

# pylint: disable=protected-access

import pytest

from tno.mpc.communication.communicators.communicator import CommunicatorState
from tno.mpc.communication.pool import Pool
from tno.mpc.communication.test.communicators.test_communicator import DummyCommunicator


@pytest.mark.asyncio
async def test_pool_async_context() -> None:
    """
    Test that the AsyncContext of Pool correctly calls `initialize` and
    `shutdown`.
    """
    comumunicator = DummyCommunicator()
    pool = Pool("local0", communicator=comumunicator)

    assert pool.communicator._state == CommunicatorState.UNINITIALIZED
    async with pool:
        assert pool.communicator._state == CommunicatorState.STARTED  # type: ignore[comparison-overlap]
    assert pool.communicator._state == CommunicatorState.STOPPED  # type: ignore[comparison-overlap]


def test_pool_add_client() -> None:
    """
    Test that the Pool correctly adds a client.
    """
    communicator = DummyCommunicator()
    pool = Pool("local0", communicator=communicator)
    pool.add_client("local1", None)

    assert len(pool._clients) == 1
    assert pool._clients["local1"]


def test_pool_cannot_add_client_twice() -> None:
    """
    Test that the Pool correctly raises an error when trying to add the same
    client twice.
    """
    communicator = DummyCommunicator()
    pool = Pool("local0", communicator=communicator)
    pool.add_client("local1", None)

    with pytest.raises(KeyError):
        pool.add_client("local1", None)


@pytest.mark.asyncio
async def test_pool_no_handler_send() -> None:
    """
    Tests raising an AttributeError exception when the handler to send a message to is not part of
    the communication pool
    """
    communicator = DummyCommunicator()
    pool = Pool("alice", communicator)

    async with pool:
        with pytest.raises(KeyError):
            await pool.send("doesnotexist", "Hello!")


@pytest.mark.asyncio
async def test_pool_no_handler_recv() -> None:
    """
    Tests raising an AttributeError exception when the handler to receive a message from is not
    part of the communication pool
    """
    communicator = DummyCommunicator()
    pool = Pool("alice", communicator)

    async with pool:
        with pytest.raises(KeyError):
            await pool.recv("doesnotexist")
