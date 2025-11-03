"""Utilities for the pytest_tno module."""

from collections.abc import AsyncIterator, Callable, Coroutine, Iterable
from typing import Any

import pytest_asyncio

from pytest_tno.tno.mpc.communication.pytest_pool_fixtures import determine_pool_scope
from tno.mpc.communication import Pool

PoolFactory = Callable[..., Coroutine[None, None, Pool]]
PoolGroupFactory = Callable[[int], Coroutine[None, None, tuple[Pool, ...]]]


@pytest_asyncio.fixture(name="_pool_factory", scope=determine_pool_scope)
async def fixture_pool_factory() -> AsyncIterator[PoolFactory]:
    """
    Factory of pool objects. Ensures proper shutdown afterwards.

    :return: Factory function for a single pool object.
    """
    from tno.mpc.communication import Pool

    pools: list[Pool] = []

    async def pool_creator(*args: Any, **kwargs: Any) -> Pool:
        r"""
        Create a Pool with the provided arguments.

        :param \*args: Positional arguments to Pool.
        :param \**kwargs: Keyword arguments to Pool.
        :return: Instantiated Pool.
        """
        # The timeout is explicitly overridden to infinity in all tests
        # to prevent timeouts in e.g. slow CI/CD pipelines. Bad
        # implementations will hang.
        kwargs.update({"timeout": None})
        pool = Pool(*args, **kwargs)
        pools.append(pool)
        return pool

    yield pool_creator

    await _shutdown_pools(pools)


async def _initialize_pools(pools: Iterable[Pool]) -> None:
    """
    Initialize all pools in the given pool groups.

    :param pools: Group of pools that are configured with servers.
    """
    for server_pool in pools:
        await server_pool.initialize()


def _reset_pools(pools: Iterable[Pool]) -> None:
    """
    Resets all pools to their initial state.

    :param pools: Pools to reset.
    """
    for pool in pools:
        pool.buffer.empty()
        for client in pool._clients.values():
            client.reset()


async def _shutdown_pools(pools: Iterable[Pool]) -> None:
    """
    Shuts down all pools.

    :param pools: Pools to shut down.
    """
    for pool in pools:
        await pool.shutdown()
