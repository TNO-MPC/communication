import pytest
from pathlib import Path

from tno.mpc.communication import Pool

from tno.mpc.communication.test import finish


@pytest.mark.asyncio
async def pool_http_local_base(id, lport, *args, ssl=False):
    if ssl:
        prefix = Path(__file__).parents[0]
        print(prefix)
        p = Pool(
            key=f"{prefix}/ssl_certs/party_{id}.key",
            cert=f"{prefix}/ssl_certs/party_{id}.crt",
            ca_cert=f"{prefix}/ssl_certs/ca.crt",
        )
    else:
        p = Pool()
    p.add_http_server(lport)
    for rname, rport in args:
        p.add_http_client(rname, "127.0.0.1", rport)
    yield p
    await p.shutdown()


@pytest.mark.asyncio
async def generate_http_test_pools(n, ssl=False):
    """
    Generates a async generator which yields n testpools which are all connected with each other.
    Connections:
    Client 0: port 4444
    Client 1: port 4445
    Client i: port 4444 + i

    Usage:
    px = generate_http_test_pools(n)
    yield await px.asend(None)  # yields a tuple of size n
    await finish(px)
    """
    p = []
    for i in range(n):
        p.append(
            pool_http_local_base(
                i,
                4444 + i,
                *[(f"local{x}", 4444 + x) for x in range(n) if x != i],
                ssl=ssl,
            )
        )
    obj = []
    for px in p:
        obj.append(await px.asend(None))
    yield tuple(obj)
    [await finish(px) for px in p]


# HTTP
@pytest.fixture
@pytest.mark.asyncio
async def pool_http_2p():
    px = generate_http_test_pools(2)
    yield await px.asend(None)
    await finish(px)


@pytest.fixture
@pytest.mark.asyncio
async def pool_http_3p():
    px = generate_http_test_pools(3)
    yield await px.asend(None)
    await finish(px)


@pytest.fixture
@pytest.mark.asyncio
async def pool_http_4p():
    px = generate_http_test_pools(4)
    yield await px.asend(None)
    await finish(px)


@pytest.fixture
@pytest.mark.asyncio
async def pool_http_5p():
    px = generate_http_test_pools(5)
    yield await px.asend(None)
    await finish(px)


# HTTPS
@pytest.fixture
@pytest.mark.asyncio
async def pool_https_2p():
    px = generate_http_test_pools(2, ssl=True)
    yield await px.asend(None)
    await finish(px)


@pytest.fixture
@pytest.mark.asyncio
async def pool_https_3p():
    px = generate_http_test_pools(3, ssl=True)
    yield await px.asend(None)
    await finish(px)


@pytest.fixture
@pytest.mark.asyncio
async def pool_https_4p():
    px = generate_http_test_pools(4, ssl=True)
    yield await px.asend(None)
    await finish(px)


@pytest.fixture
@pytest.mark.asyncio
async def pool_https_5p():
    px = generate_http_test_pools(5, ssl=True)
    yield await px.asend(None)
    await finish(px)
