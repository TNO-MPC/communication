import pytest
import asyncio

from tno.mpc import communication as com

from tno.mpc.communication.test.pool_fixtures_http import pool_http_2p
from tno.mpc.communication.test.test_packing import eq_encrypted_number


@pytest.mark.asyncio
async def test_http_server_result_available(pool_http_2p):
    pool_http_2p[0].asend("local1", "Hello!")
    res = await pool_http_2p[1].recv("local0")
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_multi(pool_http_2p):
    pool_http_2p[0].asend("local1", "Hello1!")
    pool_http_2p[0].asend("local1", "Hello2!")

    res = await pool_http_2p[1].recv("local0")
    assert res == "Hello1!"

    res = await pool_http_2p[1].recv("local0")
    assert res == "Hello2!"


@pytest.mark.asyncio
async def test_http_server_async_send(pool_http_2p):
    await pool_http_2p[0].send("local1", "Hello!")
    res = await pool_http_2p[1].recv("local0")
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_async_send_multi(pool_http_2p):
    await pool_http_2p[0].send("local1", "Hello1!")
    await pool_http_2p[0].send("local1", "Hello2!")

    res = await pool_http_2p[1].recv("local0")
    assert res == "Hello1!"

    res = await pool_http_2p[1].recv("local0")
    assert res == "Hello2!"


@pytest.mark.asyncio
async def test_http_server_future(pool_http_2p):
    send = pool_http_2p[0].send("local1", "Hello!")
    res = pool_http_2p[1].arecv("local0")

    assert asyncio.iscoroutine(send)
    assert asyncio.isfuture(res)
    await send
    await res
    assert res.result() == "Hello!"


@pytest.mark.asyncio
async def test_http_server_future_multi(pool_http_2p):
    send1 = pool_http_2p[0].send("local1", "Hello1!", msg_id="req1")
    send2 = pool_http_2p[0].send("local1", "Hello2!", msg_id="req2")

    res1 = pool_http_2p[1].arecv("local0", "req1")
    res2 = pool_http_2p[1].arecv("local0", "req2")

    await send2
    assert res2.result() == "Hello2!"

    await send1
    assert res1.result() == "Hello1!"


# Type tests
@pytest.mark.asyncio
async def test_http_server_int(pool_http_2p):
    pool_http_2p[0].asend("local1", 1234)
    res = await pool_http_2p[1].recv("local0")
    assert type(res) == int
    assert res == 1234


@pytest.mark.asyncio
async def test_http_server_float(pool_http_2p):
    pool_http_2p[0].asend("local1", 1234.4321)
    res = await pool_http_2p[1].recv("local0")
    assert type(res) == float
    assert res == 1234.4321


@pytest.mark.asyncio
async def test_http_server_bytes(pool_http_2p):
    pool_http_2p[0].asend("local1", b"Hello!")
    res = await pool_http_2p[1].recv("local0")
    assert type(res) == bytes
    assert res == b"Hello!"


@pytest.mark.asyncio
async def test_http_server_list(pool_http_2p):
    list_ = [1, 2, 3, 4]
    pool_http_2p[0].asend("local1", list_)
    res = await pool_http_2p[1].recv("local0")
    assert type(res) == list
    assert res == list_


@pytest.mark.asyncio
async def test_http_server_collection(pool_http_2p):
    collection = {"1": 1, "2": 2}
    pool_http_2p[0].asend("local1", collection)
    res = await pool_http_2p[1].recv("local0")
    assert type(res) == type(collection)
    assert res == collection


@pytest.mark.asyncio
async def test_http_server_monstrous_collection(pool_http_2p):
    collection = [
        [[1, 2], [3, 4], "5", 6],
        "7",
        "z",
        {"8": 9, 10: "11", 12.1: 13.2},
        {"14": 15, 16: "17", 18.1: 19.2},
        [[[20], "21", 22.1], "13"],
        ([1, 2], "3", 3.0, {"4": 5.0}, (6, 7)),
    ]
    pool_http_2p[0].asend("local1", collection)
    res = await pool_http_2p[1].recv("local0")
    assert type(res) == type(collection)
    assert res == collection


@pytest.mark.asyncio
async def test_http_server_string(pool_http_2p):
    pool_http_2p[0].asend("local1", "Hello!")
    res = await pool_http_2p[1].recv("local0")
    assert type(res) == str
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_custom_msg_id_int(pool_http_2p):
    pool_http_2p[0].asend("local1", "Hello!", 123)
    res = await pool_http_2p[1].recv("local0", 123)
    assert res == "Hello!"


@pytest.mark.asyncio
async def test_http_server_custom_msg_id_string(pool_http_2p):
    pool_http_2p[0].asend("local1", "Hello!", "operationX")
    res = await pool_http_2p[1].recv("local0", "operationX")
    assert res == "Hello!"


# Exception tests
@pytest.mark.asyncio
async def test_http_server_no_handler_send():
    p = com.init_pool()
    with pytest.raises(Exception):
        await p.asend("doesnotexist", "Hello!")


@pytest.mark.asyncio
async def test_http_server_no_handler_recv():
    p = com.init_pool()
    with pytest.raises(Exception):
        await p.arecv(0)
