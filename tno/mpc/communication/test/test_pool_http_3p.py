import pytest

from tno.mpc.communication.test.pool_fixtures_http import pool_http_3p, pool_https_3p


@pytest.mark.asyncio
async def send_message(pool, sender, receiver, message, msg_id=None):
    await pool[sender].send(f"local{receiver}", message, msg_id)


@pytest.mark.asyncio
async def assert_recv_message(pool, sender, receiver, message, msg_id=None):
    res = await pool[receiver].recv(f"local{sender}", msg_id)
    assert res == message


@pytest.mark.asyncio
async def assert_send_message(pool, sender, receiver, message, msg_id=None):
    await send_message(pool, sender, receiver, message, msg_id)
    await assert_recv_message(pool, sender, receiver, message, msg_id)


@pytest.mark.asyncio
async def test_http_3p_server(pool_http_3p):
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!")
    await assert_send_message(pool_http_3p, 0, 2, "Hello2!")
    await assert_send_message(pool_http_3p, 1, 0, "Hello3!")
    await assert_send_message(pool_http_3p, 1, 2, "Hello4!")
    await assert_send_message(pool_http_3p, 2, 0, "Hello5!")
    await assert_send_message(pool_http_3p, 2, 1, "Hello6!")


@pytest.mark.asyncio
async def test_https_3p_server(pool_https_3p):
    await assert_send_message(pool_https_3p, 0, 1, "Hello1!")
    await assert_send_message(pool_https_3p, 0, 2, "Hello2!")
    await assert_send_message(pool_https_3p, 1, 0, "Hello3!")
    await assert_send_message(pool_https_3p, 1, 2, "Hello4!")
    await assert_send_message(pool_https_3p, 2, 0, "Hello5!")
    await assert_send_message(pool_https_3p, 2, 1, "Hello6!")


@pytest.mark.asyncio
async def test_http_3p_server_2(pool_http_3p):
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!")
    await assert_send_message(pool_http_3p, 0, 1, "Hello2!")
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!")


@pytest.mark.asyncio
async def test_http_3p_server_3(pool_http_3p):
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
async def test_http_3p_server_msg_id(pool_http_3p):
    await assert_send_message(pool_http_3p, 0, 1, "Hello1!", "Msg ID 1")
    await assert_send_message(pool_http_3p, 0, 1, "Hello2!", "Msg ID 2")


@pytest.mark.asyncio
async def test_http_3p_server_mixed_receive(pool_http_3p):
    await send_message(pool_http_3p, 0, 1, "Hello1!")
    await send_message(pool_http_3p, 2, 1, b"Hello2!")
    await send_message(pool_http_3p, 0, 1, b"Hello3!")
    await send_message(pool_http_3p, 2, 1, "Hello4!")
    await assert_recv_message(pool_http_3p, 2, 1, b"Hello2!")
    await assert_recv_message(pool_http_3p, 2, 1, "Hello4!")
    await assert_recv_message(pool_http_3p, 0, 1, "Hello1!")
    await assert_recv_message(pool_http_3p, 0, 1, b"Hello3!")
