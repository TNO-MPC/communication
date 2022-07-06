"""
Module used to generate pool fixtures to use in unit tests.
"""

import asyncio
from asyncio import AbstractEventLoop
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Tuple

import pytest
import pytest_asyncio
from _pytest.fixtures import FixtureRequest

from tno.mpc.communication import Pool


@pytest_asyncio.fixture(scope="module")
def event_loop(  # pylint: disable=unused-argument
    request: FixtureRequest,
) -> Generator[AbstractEventLoop, None, None]:
    """
    Create an instance of the default event loop for each test case. This overrides the event_loop method from
    pytest-asyncio with a scope.

    :param request: A fixture request.
    :return: A new event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def finish(generator: AsyncGenerator[Any, None]) -> None:
    """
    Yield all items from an async generator.

    :param generator: an async generator
    """
    async for _event, *_data in generator:
        pass


@pytest.mark.asyncio
async def pool_http_local_base(
    id_: int, lport: int, *args: Tuple[str, int], ssl: bool = False
) -> AsyncGenerator[Pool, None]:
    r"""
    Generates an async generator which yields a test pool

    :param id_: the identifier of the listening client
    :param lport: the port to listen on (http server)
    :param \*args: (multiple) pair(s) specifying the clients in the form (name, client port)
    :param ssl: specify whether to use ssl certificates
    :return: a communication pool
    """
    if ssl:
        prefix = Path(__file__).parents[0]
        pool = Pool(
            key=f"{prefix}/ssl_certs/party_{id_}.key",
            cert=f"{prefix}/ssl_certs/party_{id_}.crt",
            ca_cert=f"{prefix}/ssl_certs/ca.crt",
        )
    else:
        pool = Pool()
    pool.add_http_server(port=lport)
    for client_name, client_port in args:
        pool.add_http_client(client_name, "127.0.0.1", client_port)
    yield pool
    await pool.shutdown()


@pytest.mark.asyncio
async def generate_http_test_pools(
    clients: int, ssl: bool = False
) -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Generates an async generator which yields n test pools which are all connected with each other.
    Connections:
    Client 0: port 4444 + 10 * n
    Client 1: port 4445 + 10 * n
    Client i: port 4444 + 10 * n + i

    Usage:
    pools = generate_http_test_pools(n)
    yield await pools.asend(None)  # yields a tuple of size n
    await finish(pools)

    :param clients: number of clients (n)
    :param ssl: specify whether to use ssl certificates
    :return: a collection of communication pools
    """
    pools = []
    base_port = 4444 + clients * 10
    for client in range(clients):
        pools.append(
            pool_http_local_base(
                client,
                base_port + client,
                *[(f"local{_}", base_port + _) for _ in range(clients) if _ != client],
                ssl=ssl,
            )
        )
    obj = []
    for pool in pools:
        obj.append(await pool.asend(None))
    yield tuple(obj)
    await asyncio.gather(*[finish(pool) for pool in pools])


# HTTP
@pytest_asyncio.fixture(name="pool_http_2p", scope="module")
async def fixture_pool_http_2p() -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Creates a collection of 2 communication pools

    :return: a collection of communication pools
    """
    pools = generate_http_test_pools(2)
    yield await pools.asend(None)
    await finish(pools)


@pytest_asyncio.fixture(name="pool_http_3p", scope="module")
async def fixture_pool_http_3p() -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Creates a collection of 3 communication pools

    :return: a collection of communication pools
    """
    pools = generate_http_test_pools(3)
    yield await pools.asend(None)
    await finish(pools)


@pytest_asyncio.fixture(name="pool_http_4p", scope="module")
async def fixture_pool_http_4p() -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Creates a collection of 4 communication pools

    :return: a collection of communication pools
    """
    pools = generate_http_test_pools(4)
    yield await pools.asend(None)
    await finish(pools)


@pytest_asyncio.fixture(name="pool_http_5p", scope="module")
async def fixture_pool_http_5p() -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Creates a collection of 5 communication pools

    :return: a collection of communication pools
    """
    pools = generate_http_test_pools(5)
    yield await pools.asend(None)
    await finish(pools)


# HTTPS
@pytest_asyncio.fixture(name="pool_https_2p", scope="function")
async def fixture_pool_https_2p() -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Creates a collection of 2 communication pools using SSL/TLS

    :return: a collection of communication pools
    """
    pools = generate_http_test_pools(2, ssl=True)
    yield await pools.asend(None)
    await finish(pools)


@pytest_asyncio.fixture(name="pool_https_3p", scope="function")
async def fixture_pool_https_3p() -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Creates a collection of 3 communication pools using SSL/TLS

    :return: a collection of communication pools
    """
    pools = generate_http_test_pools(3, ssl=True)
    yield await pools.asend(None)
    await finish(pools)


@pytest_asyncio.fixture(name="pool_https_4p", scope="function")
async def fixture_pool_https_4p() -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Creates a collection of 4 communication pools using SSL/TLS

    :return: a collection of communication pools
    """
    pools = generate_http_test_pools(4, ssl=True)
    yield await pools.asend(None)
    await finish(pools)


@pytest_asyncio.fixture(name="pool_https_5p", scope="function")
async def fixture_pool_https_5p() -> AsyncGenerator[Tuple[Pool, ...], None]:
    """
    Creates a collection of 5 communication pools using SSL/TLS

    :return: a collection of communication pools
    """
    pools = generate_http_test_pools(5, ssl=True)
    yield await pools.asend(None)
    await finish(pools)
