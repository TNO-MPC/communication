"""
This module tests the creation of communication pools.
"""

import asyncio
from typing import Any

from tno.mpc.communication import Pool


async def send_recv(sending_pool: Pool, receiving_pool: Pool) -> Any:
    """
    Send and receives message from one communication pool to the other.

    :param sending_pool: the pool that sends the message
    :param receiving_pool: the pool that receives the message
    :return: the received message
    """
    await sending_pool.send("test_client", 42)
    return await receiving_pool.recv("test_client")


def test_sync_pool_creation() -> None:
    """
    Tests creation and working of communication pools
    """
    pool = Pool()
    pool.add_http_server(port=4242)
    pool.add_http_client("test_client", "127.0.0.1", port=9193)

    pool_2 = Pool()
    pool_2.add_http_server(port=9193)
    pool_2.add_http_client("test_client", "127.0.0.1", port=4242)

    assert pool.http_server is not None and pool.http_server.port == 4242
    assert pool.pool_handlers["test_client"].port == 9193
    assert pool_2.http_server is not None and pool_2.http_server.port == 9193
    assert pool_2.pool_handlers["test_client"].port == 4242

    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(send_recv(pool, pool_2)) == 42
    assert loop.run_until_complete(send_recv(pool_2, pool)) == 42
