"""
This module tests the communication between three communication pools.
"""
import asyncio
from typing import Any, List, Optional, Tuple

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
async def broadcast_message(
    pools: Tuple[Pool, ...],
    sender: int,
    receivers: List[int],
    message: Any,
    msg_id: str,
) -> None:
    """
    Send a message

    :param pools: the communication pools to use
    :param sender: the id of the sending party
    :param receivers: a list with ids of the receiving party
    :param message: the message to send
    :param msg_id: the message id to use
    """
    await pools[sender].broadcast(
        message, msg_id, [f"local{receiver}" for receiver in receivers]
    )


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
async def assert_send_recv_all_message(
    pools: Tuple[Pool, ...],
    receiver: int,
    senders: List[int],
    message: Any,
    msg_id: Optional[str] = None,
) -> None:
    """
    Sends a message to one party from each other party and validate whether it is received correctly.

    :param pools: the communication pools to use
    :param receiver: the id of the receiving party
    :param senders: the ids of the sending parties.
    :param message: the message
    :param msg_id: the message id to use
    """
    await asyncio.gather(
        *(send_message(pools, sender, receiver, message, msg_id) for sender in senders)
    )
    res = await pools[receiver].recv_all(
        [f"local{sender}" for sender in senders], msg_id=msg_id
    )

    received_from = []
    for sender, received_message in res:
        assert received_message == message
        received_from.append(int(sender[5:]))
    assert sorted(received_from) == sorted(senders)


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
async def assert_broadcast_message(
    pools: Tuple[Pool, ...],
    sender: int,
    receivers: List[int],
    message: Any,
    msg_id: str,
) -> None:
    """
    Send a message

    :param pools: the communication pools to use
    :param sender: the id of the sending party
    :param receivers: a list with ids of the receiving party
    :param message: the message to send
    :param msg_id: the message id to use
    """
    await broadcast_message(pools, sender, receivers, message, msg_id)
    await asyncio.gather(
        *(
            assert_recv_message(pools, sender, receiver, message, msg_id)
            for receiver in receivers
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            assert_send_message(pool_http_3p, 0, 1, "Hello1!"),
            assert_send_message(pool_http_3p, 0, 2, "Hello2!"),
            assert_send_message(pool_http_3p, 1, 0, "Hello3!"),
            assert_send_message(pool_http_3p, 1, 2, "Hello4!"),
            assert_send_message(pool_http_3p, 2, 0, "Hello5!"),
            assert_send_message(pool_http_3p, 2, 1, "Hello6!"),
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server_broadcast(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple broadcast messages between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            assert_broadcast_message(pool_http_3p, 0, [1, 2], "Hello1!", "id1"),
            assert_broadcast_message(pool_http_3p, 1, [0, 2], "Hello2!", "id2"),
            assert_broadcast_message(pool_http_3p, 2, [0, 1], "Hello3!", "id3"),
            assert_broadcast_message(pool_http_3p, 0, [1], "Hello1!", "id4"),
            assert_broadcast_message(pool_http_3p, 1, [2], "Hello2!", "id5"),
            assert_broadcast_message(pool_http_3p, 2, [0], "Hello3!", "id6"),
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server_2(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            assert_send_message(pool_http_3p, 0, 1, "Hello1!"),
            assert_send_message(pool_http_3p, 0, 1, "Hello2!"),
            assert_send_message(pool_http_3p, 0, 1, "Hello1!"),
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server_broadcast_2(
    pool_http_3p: Tuple[Pool, Pool, Pool]
) -> None:
    """
    Tests sending and receiving of multiple broadcast messages between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            assert_broadcast_message(pool_http_3p, 0, [1, 2], "Hello1!", "id1"),
            assert_broadcast_message(pool_http_3p, 0, [1, 2], "Hello2!", "id2"),
            assert_broadcast_message(pool_http_3p, 0, [1, 2], "Hello3!", "id3"),
            assert_broadcast_message(pool_http_3p, 0, [1], "Hello1!", "id4"),
            assert_broadcast_message(pool_http_3p, 0, [2], "Hello2!", "id5"),
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server_3(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            assert_send_message(pool_http_3p, 0, 1, "Hello1!"),
            assert_send_message(pool_http_3p, 0, 2, "Hello2!"),
            assert_send_message(pool_http_3p, 1, 0, "Hello3!"),
            assert_send_message(pool_http_3p, 1, 2, "Hello4!"),
            assert_send_message(pool_http_3p, 2, 0, "Hello5!"),
            assert_send_message(pool_http_3p, 2, 1, "Hello6!"),
            assert_send_message(pool_http_3p, 0, 1, "Hello7!"),
            assert_send_message(pool_http_3p, 0, 2, "Hello8!"),
            assert_send_message(pool_http_3p, 1, 0, "Hello9!"),
            assert_send_message(pool_http_3p, 1, 2, "Hello10!"),
            assert_send_message(pool_http_3p, 2, 0, "Hello11!"),
            assert_send_message(pool_http_3p, 2, 1, "Hello12!"),
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server_msg_id(pool_http_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools with a message id

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            assert_send_message(pool_http_3p, 0, 1, "Hello1!", "Msg ID 1"),
            assert_send_message(pool_http_3p, 0, 1, "Hello2!", "Msg ID 2"),
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server_mixed_receive(
    pool_http_3p: Tuple[Pool, Pool, Pool]
) -> None:
    """
    Tests sending and receiving of multiple messages of varying types between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            send_message(pool_http_3p, 0, 1, "Hello1!"),
            send_message(pool_http_3p, 2, 1, b"Hello2!"),
            send_message(pool_http_3p, 0, 1, b"Hello3!"),
            send_message(pool_http_3p, 2, 1, "Hello4!"),
            assert_recv_message(pool_http_3p, 2, 1, b"Hello2!"),
            assert_recv_message(pool_http_3p, 2, 1, "Hello4!"),
            assert_recv_message(pool_http_3p, 0, 1, "Hello1!"),
            assert_recv_message(pool_http_3p, 0, 1, b"Hello3!"),
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server_recv_all_mixed(
    pool_http_3p: Tuple[Pool, Pool, Pool]
) -> None:
    """
    Test receiving of a message from each other party using the recv_all method.

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            assert_send_recv_all_message(pool_http_3p, 0, [1, 2], "Hello1!", "id1"),
            assert_send_recv_all_message(pool_http_3p, 0, [1, 2], b"Hello2!", "id2"),
            assert_send_recv_all_message(pool_http_3p, 0, [1, 2], b"Hello3!", "id3"),
            assert_send_recv_all_message(pool_http_3p, 0, [1], "Hello1!", "id4"),
            assert_send_recv_all_message(pool_http_3p, 0, [2], b"Hello2!", "id5"),
        )
    )


@pytest.mark.asyncio
async def test_http_3p_server_mixed_broadcast(
    pool_http_3p: Tuple[Pool, Pool, Pool]
) -> None:
    """
    Tests sending and receiving of multiple broadcast messages of various types between three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    await asyncio.gather(
        *(
            assert_broadcast_message(pool_http_3p, 0, [1, 2], "Hello1!", "id1"),
            assert_broadcast_message(pool_http_3p, 0, [1, 2], b"Hello2!", "id2"),
            assert_broadcast_message(pool_http_3p, 0, [1, 2], b"Hello3!", "id3"),
            assert_broadcast_message(pool_http_3p, 0, [1], "Hello1!", "id4"),
            assert_broadcast_message(pool_http_3p, 0, [2], b"Hello2!", "id5"),
        )
    )


@pytest.mark.asyncio
async def test_broadcast_msg_id_string_prefix(
    pool_http_3p: Tuple[Pool, Pool, Pool]
) -> None:
    """
    Tests asynchronous sending and receiving of a string with a prefixed custom message id between
    three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    pool_http_3p[0].update_msg_prefix("prefix")
    pool_http_3p[1].update_msg_prefix("prefix")
    pool_http_3p[2].update_msg_prefix("prefix")

    await assert_broadcast_message(pool_http_3p, 0, [1, 2], "Hello1!", "id1")


@pytest.mark.asyncio
async def test_broadcast_msg_id_string_prefix_deviation(
    pool_http_3p: Tuple[Pool, Pool, Pool]
) -> None:
    """
    Tests asynchronous sending and receiving of a string with a prefixed custom message id between
    three communication pools

    :param pool_http_3p: collection of three communication pools
    """
    pool_http_3p[0].update_msg_prefix("prefix")
    pool_http_3p[1].update_msg_prefix("prefix")
    pool_http_3p[2].update_msg_prefix("prefix")
    list(pool_http_3p[0].pool_handlers.values())[0].msg_prefix = "something different"

    with pytest.raises(ValueError):
        await assert_broadcast_message(pool_http_3p, 0, [1, 2], "Hello1!", "id1")
