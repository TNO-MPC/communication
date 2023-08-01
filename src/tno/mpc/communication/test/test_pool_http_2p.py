"""
This module tests the communication between two communication pools.
"""
from __future__ import annotations

import asyncio
import itertools

import pytest

from tno.mpc.communication import Pool, Serialization
from tno.mpc.communication.test.test_packing import (
    ClassCorrectKwargs,
    ClassCorrectKwargs2,
)


@pytest.mark.asyncio
async def test_http_server_result_available(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests sending and receiving of a message between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    await http_pool_duo[0].send("local1", "Hello!")
    res = await http_pool_duo[1].recv("local0")
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_multi(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    await http_pool_duo[0].send("local1", "Hello1!")
    await http_pool_duo[0].send("local1", "Hello2!")

    res = await http_pool_duo[1].recv("local0")
    assert res == "Hello1!"

    res = await http_pool_duo[1].recv("local0")
    assert res == "Hello2!"


@pytest.mark.asyncio
async def test_http_server_async_send(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a message between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    await http_pool_duo[0].send("local1", "Hello!")
    res = await http_pool_duo[1].recv("local0")
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_async_send_multi(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of multiple messages between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    await http_pool_duo[0].send("local1", "Hello1!")
    await http_pool_duo[0].send("local1", "Hello2!")

    res = await http_pool_duo[1].recv("local0")
    assert res == "Hello1!"

    res = await http_pool_duo[1].recv("local0")
    assert res == "Hello2!"


@pytest.mark.asyncio
async def test_http_server_future(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests sending and asynchronous receiving of a message between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    send = http_pool_duo[0].send("local1", "Hello!")
    res = http_pool_duo[1].arecv("local0")

    assert asyncio.iscoroutine(send)
    assert asyncio.isfuture(res)
    await send
    await res
    assert res.result() == "Hello!"


@pytest.mark.asyncio
async def test_http_server_future_multi(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests sending and asynchronous receiving of multiple messages between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    send1 = http_pool_duo[0].send("local1", "Hello1!", msg_id="req1")
    send2 = http_pool_duo[0].send("local1", "Hello2!", msg_id="req2")

    res1 = http_pool_duo[1].arecv("local0", "req1")
    res2 = http_pool_duo[1].arecv("local0", "req2")

    await send2
    assert res2.result() == "Hello2!"

    await send1
    assert res1.result() == "Hello1!"


# Type tests
@pytest.mark.asyncio
async def test_http_server_int(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of an integer between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    http_pool_duo[0].asend("local1", 1234)
    res = await http_pool_duo[1].recv("local0")
    assert isinstance(res, int)
    assert res == 1234


@pytest.mark.asyncio
async def test_http_server_float(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a float between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    http_pool_duo[0].asend("local1", 1234.4321)
    res = await http_pool_duo[1].recv("local0")
    assert isinstance(res, float)
    assert res == 1234.4321


@pytest.mark.asyncio
async def test_http_server_bytes(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a bytes object between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    http_pool_duo[0].asend("local1", b"Hello!")
    res = await http_pool_duo[1].recv("local0")
    assert isinstance(res, bytes)
    assert res == b"Hello!"


@pytest.mark.asyncio
async def test_http_server_list(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a list between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    list_ = [1, 2, 3, 4]
    http_pool_duo[0].asend("local1", list_)
    res = await http_pool_duo[1].recv("local0")
    assert isinstance(res, list)
    assert res == list_


@pytest.mark.asyncio
async def test_http_server_collection(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a dictionary between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    collection = {"1": 1, "2": 2}
    http_pool_duo[0].asend("local1", collection)
    res = await http_pool_duo[1].recv("local0")
    assert isinstance(collection, type(res))
    assert res == collection


@pytest.mark.asyncio
async def test_http_server_custom_kwargs(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a custom object making use of keyword arguments
    between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    ClassCorrectKwargs.origin = []
    ClassCorrectKwargs.destination = []
    Serialization.clear_serialization_logic()
    Serialization.register_class(ClassCorrectKwargs)
    obj = ClassCorrectKwargs([1, 2, 3, 4], "test")
    http_pool_duo[0].asend("local1", obj)
    res = await http_pool_duo[1].recv("local0")
    assert isinstance(obj, type(res))
    assert res.name == obj.name
    assert res.values == obj.values
    assert ClassCorrectKwargs.destination[0] == http_pool_duo[0].pool_handlers["local1"]
    assert ClassCorrectKwargs.origin[0] == http_pool_duo[1].pool_handlers["local0"]
    ClassCorrectKwargs.origin = []
    ClassCorrectKwargs.destination = []


@pytest.mark.asyncio
async def test_http_server_custom_kwargs2(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a custom object making use of keyword arguments
    between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    ClassCorrectKwargs.origin = []
    ClassCorrectKwargs.destination = []
    Serialization.clear_serialization_logic()
    Serialization.register_class(ClassCorrectKwargs)
    Serialization.register_class(ClassCorrectKwargs2)
    obj = ClassCorrectKwargs([1, 2, 3, 4], "test")
    obj2 = ClassCorrectKwargs2([5, 6, 7, 8], obj)
    http_pool_duo[0].asend("local1", obj2)
    res = await http_pool_duo[1].recv("local0")
    assert isinstance(obj2, type(res))
    assert res.values == obj2.values
    assert res.other.name == obj2.other.name
    assert res.other.values == obj2.other.values
    assert ClassCorrectKwargs.destination[0] == http_pool_duo[0].pool_handlers["local1"]
    assert ClassCorrectKwargs.origin[0] == http_pool_duo[1].pool_handlers["local0"]
    ClassCorrectKwargs.origin = []
    ClassCorrectKwargs.destination = []


@pytest.mark.asyncio
async def test_http_server_string(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a string between two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    http_pool_duo[0].asend("local1", "Hello!")
    res = await http_pool_duo[1].recv("local0")
    assert isinstance(res, str)
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_custom_msg_id_int(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of an int with a custom message id between two
    communication pools

    :param http_pool_duo: collection of two communication pools
    """
    http_pool_duo[0].asend("local1", "Hello!", str(123))
    res = await http_pool_duo[1].recv("local0", str(123))
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_custom_msg_id_string(
    http_pool_duo: tuple[Pool, Pool]
) -> None:
    """
    Tests asynchronous sending and receiving of a string with a custom message id between two
    communication pools

    :param http_pool_duo: collection of two communication pools
    """
    http_pool_duo[0].asend("local1", "Hello!", "operationX")
    res = await http_pool_duo[1].recv("local0", "operationX")
    assert res == "Hello!"


# Exception tests
@pytest.mark.asyncio
async def test_http_server_no_handler_send() -> None:
    """
    Tests raising an AttributeError exception when the handler to send a message to is not part of
    the communication pool
    """
    pool = Pool()
    with pytest.raises(AttributeError):
        pool.asend("doesnotexist", "Hello!")


@pytest.mark.asyncio
async def test_http_server_no_handler_recv() -> None:
    """
    Tests raising an AttributeError exception when the handler to receive a message from is not
    part of the communication pool
    """
    pool = Pool()
    with pytest.raises(AttributeError):
        await pool.arecv("doesnotexist")


@pytest.mark.asyncio
async def test_http_server_async_send_prefix(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Tests asynchronous sending and receiving of a message between two communication pools with
    a prefixed msg_id

    :param http_pool_duo: collection of two communication pools
    """
    http_pool_duo[0].update_msg_prefix("prefix")
    http_pool_duo[1].update_msg_prefix("prefix")
    await http_pool_duo[0].send("local1", "Hello!")
    assert next(iter(http_pool_duo[1].pool_handlers["local0"].buffer)).startswith(
        "prefix"
    )
    res = await http_pool_duo[1].recv("local0")
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_custom_msg_id_string_prefix(
    http_pool_duo: tuple[Pool, Pool]
) -> None:
    """
    Tests asynchronous sending and receiving of a string with a prefixed custom message id between
    two communication pools

    :param http_pool_duo: collection of two communication pools
    """
    http_pool_duo[0].update_msg_prefix("prefix")
    http_pool_duo[1].update_msg_prefix("prefix")

    http_pool_duo[0].asend("local1", "Hello!", "operationX")
    res = await http_pool_duo[1].recv("local0", "operationX")
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_async_send_multi_prefix(
    http_pool_duo: tuple[Pool, Pool]
) -> None:
    """
    Tests asynchronous sending and receiving of a message between two communication pools with
    varying prefixed msg_id

    :param http_pool_duo: collection of two communication pools
    """
    # Ensure prefixes are None
    http_pool_duo[0].update_msg_prefix(None)
    http_pool_duo[1].update_msg_prefix(None)
    assert all(
        _.msg_prefix is None
        for _ in itertools.chain(
            http_pool_duo[0].pool_handlers.values(),
            http_pool_duo[1].pool_handlers.values(),
        )
    )

    await http_pool_duo[0].send("local1", "Hello!", msg_id="test")
    assert next(iter(http_pool_duo[1].pool_handlers["local0"].buffer)) == "test"
    res = await http_pool_duo[1].recv("local0", "test")

    http_pool_duo[0].update_msg_prefix("prefix")
    http_pool_duo[1].update_msg_prefix("prefix")
    await http_pool_duo[0].send("local1", "Hello!_test", msg_id="test")
    assert next(iter(http_pool_duo[1].pool_handlers["local0"].buffer)) == "prefixtest"
    res = await http_pool_duo[1].recv("local0", "test")
    assert res == "Hello!_test"

    http_pool_duo[0].update_msg_prefix("prefix_2")
    http_pool_duo[1].update_msg_prefix("prefix_2")
    await http_pool_duo[0].send("local1", "Hello!_test_no2", msg_id="test")
    assert next(iter(http_pool_duo[1].pool_handlers["local0"].buffer)) == "prefix_2test"
    res = await http_pool_duo[1].recv("local0", "test")
    assert res == "Hello!_test_no2"


@pytest.mark.asyncio
async def test_http_server_recv_timeout(http_pool_duo: tuple[Pool, Pool]) -> None:
    """
    Verify that the timeout parameter in pool.recv is respected. Fails if the thread hangs.

    :param http_pool_duo: collection of two communication pools
    """

    async def failing_sender() -> None:
        pass

    async def receiver_with_timeout() -> None:
        await http_pool_duo[1].recv("local0", timeout=1)

    async def test_attempt_to_communicate() -> None:
        with pytest.raises((TimeoutError, asyncio.TimeoutError)):
            await asyncio.gather(failing_sender(), receiver_with_timeout())

    try:
        await asyncio.wait_for(test_attempt_to_communicate(), timeout=2)
    except (TimeoutError, asyncio.TimeoutError):
        assert False, "Receiving pool thread hangs."
