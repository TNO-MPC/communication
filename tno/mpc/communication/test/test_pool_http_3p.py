"""
This module tests the communication between three communication pools.
"""

from typing import Any, Optional, Tuple

import pytest

from tno.mpc.communication import Pool
from tno.mpc.communication.test import (  # pylint: disable=unused-import
    event_loop,
    fixture_pool_http_3p,
)


@pytest.mark.asyncio
async def send_message(
    pools: Tuple[Pool, ...],
    sender: int,
    receiver: int,
    message: Any,
    msg_id: Optional[str] = None,
) -> None:
    """
    Send a message

    :param pools: the communication pools to use
    :param sender: the id of the sending party
    :param receiver: the id of the receiving party
    :param message: the message to send
    :param msg_id: the message id to use
    """
    await pools[sender].send(f"local{receiver}", message, msg_id)


@pytest.mark.asyncio
async def assert_recv_message(
    pools: Tuple[Pool, ...],
    sender: int,
    receiver: int,
    message: Any,
    msg_id: Optional[str] = None,
) -> None:
    """
    Receives a message and validates whether it is in line with the expected message

    :param pools: the communication pools to use
    :param sender: the id of the sending party
    :param receiver: the id of the receiving party
    :param message: the expected message
    :param msg_id: the message id of the expected message
    """
    res = await pools[receiver].recv(f"local{sender}", msg_id)
    assert res == message


@pytest.mark.asyncio
async def assert_send_message(
    pools: Tuple[Pool, ...],
    sender: int,
    receiver: int,
    message: Any,
    msg_id: Optional[str] = None,
) -> None:
    """
    Sends a message and validates whether it is received correctly

    :param pools: the communication pools to use
    :param sender: the id of the sending party
    :param receiver: the id of the receiving party
    :param message: the message
    :param msg_id: the message id to use
    """
    await send_message(pools, sender, receiver, message, msg_id)
    await assert_recv_message(pools, sender, receiver, message, msg_id)


@pytest.mark.asyncio
async def test_http_3p_server(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!")
    await assert_send_message(pool_http_3p, 0, 2, "Hello2!")
    await assert_send_message(pool_http_3p, 1, 0, "Hello3!")
    await assert_send_message(pool_http_3p, 1, 2, "Hello4!")
    await assert_send_message(pool_http_3p, 2, 0, "Hello5!")
    await assert_send_message(pool_http_3p, 2, 1, "Hello6!")


@pytest.mark.asyncio
async def test_http_3p_server_2(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!")
    await assert_send_message(pool_http_3p, 0, 1, "Hello2!")
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!")


@pytest.mark.asyncio
async def test_http_3p_server_3(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!")
    await assert_send_message(pool_http_3p, 0, 2, "Hello2!")
    await assert_send_message(pool_http_3p, 1, 0, "Hello3!")
    await assert_send_message(pool_http_3p, 1, 2, "Hello4!")
    await assert_send_message(pool_http_3p, 2, 0, "Hello5!")
    await assert_send_message(pool_http_3p, 2, 1, "Hello6!")

    await assert_send_message(pool_http_3p, 0, 1, "Hello7!")
    await assert_send_message(pool_http_3p, 0, 2, "Hello8!")
    await assert_send_message(pool_http_3p, 1, 0, "Hello9!")
    await assert_send_message(pool_http_3p, 1, 2, "Hello10!")
    await assert_send_message(pool_http_3p, 2, 0, "Hello11!")
    await assert_send_message(pool_http_3p, 2, 1, "Hello12!")


@pytest.mark.asyncio
async def test_http_3p_server_msg_id(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools with a message id

    :param pool_http_3p: collection of three communication pools
    """
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!", "Msg ID 1")
    await assert_send_message(pool_http_3p, 0, 1, "Hello2!", "Msg ID 2")


@pytest.mark.asyncio
async def test_http_3p_server_mixed_receive(
    pool_http_3p: Tuple[Pool, Pool, Pool]
) -> None:
    """
    Tests sending and receiving of multiple messages of varying types between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await send_message(pool_http_3p, 0, 1, "Hello1!")
    await send_message(pool_http_3p, 2, 1, b"Hello2!")
    await send_message(pool_http_3p, 0, 1, b"Hello3!")
    await send_message(pool_http_3p, 2, 1, "Hello4!")
    await assert_recv_message(pool_http_3p, 2, 1, b"Hello2!")
    await assert_recv_message(pool_http_3p, 2, 1, "Hello4!")
    await assert_recv_message(pool_http_3p, 0, 1, "Hello1!")
    await assert_recv_message(pool_http_3p, 0, 1, b"Hello3!")
