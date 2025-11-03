"""
Fixtures for creating pools with MockCommunicators.
"""

import itertools
from typing import cast

import pytest_asyncio
from aiocache import cached

from pytest_tno.tno.mpc.communication.pytest_pool_fixtures import determine_pool_scope
from pytest_tno.tno.mpc.communication.utils import (  # nopycln: import # fixture_pool_factory required for pytest fixture discovery
    PoolFactory,
    PoolGroupFactory,
    _initialize_pools,
    _reset_pools,
    fixture_pool_factory,
)
from tno.mpc.communication.communicators.mock_communicator import (
    MockCommunicator,
    MockConnection,
)
from tno.mpc.communication.pool import Pool


@pytest_asyncio.fixture(name="mock_pool_duo")
async def fixture_mock_pool_duo(
    mock_pool_group_factory: PoolGroupFactory,
) -> tuple[Pool, Pool]:
    """
    Two pools with mock communicators.

    :param mock_pool_group_factory: factory for creating a mock pool group.
    :return: Two pools with mock communicators.
    """
    return cast(tuple[Pool, Pool], await mock_pool_group_factory(2))


@pytest_asyncio.fixture(name="mock_pool_trio")
async def fixture_mock_pool_trio(
    mock_pool_group_factory: PoolGroupFactory,
) -> tuple[Pool, Pool, Pool]:
    """
    Three pools with mock communicators.

    :param mock_pool_group_factory: factory for creating a mock pool group.
    :return: Three pools with mock communicators.
    """
    return cast(tuple[Pool, Pool, Pool], await mock_pool_group_factory(3))


@pytest_asyncio.fixture(name="mock_pool_group_factory")
async def fixture_mock_pool_group_factory(
    _scoped_mock_pool_group_factory: PoolGroupFactory,
) -> PoolGroupFactory:
    """
    Factory for creating a mock pool group with the requested number of pools.
    Ensures the pools are reset before each use.

    :param _scoped_mock_pool_group_factory: Factory for creating a mock pool group with
        any pytest scope.
    :return: Factory for creating a mock pool group with the requested number of pools.
    """

    async def resetted_mock_pool_group_factory(n_pools: int) -> tuple[Pool, ...]:
        """
        Factory for creating a mock pool group with the requested number of pools.
        Ensures the pools are reset before each use.

        :param n_pools: Number of pools in the group.
        :return: Group of pool objects with mutual communication configured.
        """
        pools = await _scoped_mock_pool_group_factory(n_pools)
        _reset_pools(pools)
        return pools

    return resetted_mock_pool_group_factory


@pytest_asyncio.fixture(
    name="_scoped_mock_pool_group_factory",
    scope=determine_pool_scope,
)
async def fixture_scoped_mock_pool_group_factory(
    _pool_factory: PoolFactory,
) -> PoolGroupFactory:
    """
    Factory for creating a mock pool group with the requested number of pools.

    :param _pool_factory: Factory for creating and maintaining a single pool.
    :return: Factory for creating a mock pool group with the requested number of pools.
    """

    @cached()
    async def mock_pool_group_factory(
        n_pools: int,
    ) -> tuple[Pool, ...]:
        """
        Factory for creating a mock pool group with the requested number of pools.

        :param n_pools: Number of pools in the group.
        :return: Group of pool objects with mutual communication configured.
        """
        pools = [
            await _pool_factory(
                name=f"local{i}", communicator=MockCommunicator(f"local{i}")
            )
            for i in range(n_pools)
        ]

        for server_pool, (client_nr, client_pool) in itertools.product(
            pools, enumerate(pools)
        ):
            if server_pool == client_pool:
                continue
            assert isinstance(client_pool.communicator, MockCommunicator)
            configuration = MockConnection(client_pool.communicator)
            server_pool.add_client(f"local{client_nr}", configuration)

        await _initialize_pools(pools)
        return tuple(pools)

    return mock_pool_group_factory
