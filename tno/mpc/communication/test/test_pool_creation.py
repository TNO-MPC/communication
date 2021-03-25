import asyncio
import pytest

from tno.mpc.communication import Pool


def test_sync_pool_creation():
    pool = Pool()
    pool.add_http_server(port=4242)
    pool.add_http_client("test_client", "127.0.0.1", port=9193)

    pool2 = Pool()
    pool2.add_http_server(port=9193)
    pool2.add_http_client("test_client", "127.0.0.1", port=4242)

    assert pool.http_server.port == 4242
    assert pool.pool_handlers["test_client"].port == 9193
    assert pool2.http_server.port == 9193
    assert pool2.pool_handlers["test_client"].port == 4242

    async def send_recv(pool, pool2):
        await pool.send("test_client", 42)
        return await pool2.recv("test_client")

    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(send_recv(pool, pool2)) == 42
    assert loop.run_until_complete(send_recv(pool2, pool)) == 42
