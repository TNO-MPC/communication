"""
Pytest fixtures for generating groups of pools.
"""

# pylint: disable=import-outside-toplevel  # toplevel import messes up coverage results
from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable, Sequence
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
from tno.mpc.communication import HttpCommunicator, HttpConnection, Pool


@pytest_asyncio.fixture(name="http_pool_duo")
async def fixture_http_pool_duo(
    http_pool_group_factory: PoolGroupFactory,
) -> tuple[Pool, Pool]:
    """
    Two communication pools without TLS/SSL.

    :param http_pool_group_factory: Factory for creating a HTTP pool group.
    :return: Two communication pools without TLS/SSL.
    """
    return cast(tuple[Pool, Pool], await http_pool_group_factory(2))


@pytest_asyncio.fixture(name="http_pool_trio")
async def fixture_http_pool_trio(
    http_pool_group_factory: PoolGroupFactory,
) -> tuple[Pool, Pool, Pool]:
    """
    Three communication pools without TLS/SSL.

    :param http_pool_group_factory: Factory for creating a HTTP pool group.
    :return: Three communication pools without TLS/SSL.
    """
    return cast(tuple[Pool, Pool, Pool], await http_pool_group_factory(3))


@pytest_asyncio.fixture(name="http_pool_group_factory")
async def fixture_http_pool_group_factory(
    _scoped_http_pool_group_factory: PoolGroupFactory,
) -> PoolGroupFactory:
    """
    Factory for creating a HTTP pool group with the requested number of pools.
    Ensures the pools are reset before each usage.

    The pool group is configured without SSL certificates.

    :param _scoped_http_pool_group_factory: Factory for creating a HTTP pool group with
        any pytest scope.
    :return: Factory for creating a HTTP pool group with the requested number of pools.
    """

    async def resetted_http_pool_group_factory(n_pools: int) -> tuple[Pool, ...]:
        """
        Factory for creating a HTTP pool group with the requested number of pools.
        Ensures the pools are reset before each usage.

        :param n_pools: Number of pools in the group.
        :return: Group of pool objects with mutual communication configured.
        """
        pools = await _scoped_http_pool_group_factory(n_pools)
        _reset_pools(pools)
        return pools

    return resetted_http_pool_group_factory


@pytest_asyncio.fixture(
    name="_scoped_http_pool_group_factory",
    scope=determine_pool_scope,
)
async def fixture_scoped_http_pool_group_factory(
    _pool_factory: PoolFactory,
    unused_tcp_port_factory: Callable[[], int],
) -> PoolGroupFactory:
    """
    Factory for creating a HTTP pool group with the requested number of pools.

    The pool group is configured without SSL certificates. The pools do not reset
    between invocations (e.g. buffers, client message counters).

    :param _pool_factory: Factory for creating and maintaining a single pool.
    :param unused_tcp_port_factory: pytest_asyncio fixture for getting unused tcp_ports.
    :return: Factory for creating a HTTP pool group with the requested number of pools.
    """

    @cached()
    async def http_pool_group_factory(n_pools: int) -> tuple[Pool, ...]:
        """
        Factory for creating a HTTP pool group with the requested number of pools.

        :param n_pools: Number of pools in the group.
        :return: Group of pool objects with mutual communication configured.
        """
        if n_pools < 1 or n_pools > 9:
            raise ValueError(
                f"The test pool generator can create pool groups with 1-9 clients, but {n_pools} clients were requested."
            )
        ports = [unused_tcp_port_factory() for _ in range(n_pools)]
        return await _generate_test_pools(_pool_factory_=_pool_factory, ports=ports)

    return http_pool_group_factory


async def _generate_test_pools(
    _pool_factory_: PoolFactory,
    ports: Sequence[int],
) -> tuple[Pool, ...]:
    """
    Generates a group of communication pools and sets up the communication between them.

    :param _pool_factory_: Factory of pool objects.
    :param ports: Ports for pools.
    :raise ValueError: If the number of clients exceeds nine.
    :return: Fully initialized pools.
    """
    communicators = _create_communicator_group(ports)
    pools = await _create_pool_group(_pool_factory_, communicators)
    _configure_clients(pools)
    await _initialize_pools(pools)
    return tuple(pools)


def _create_communicator_group(ports: Sequence[int]) -> list[HttpCommunicator]:
    """
    Communicator group initializer.

    Initializes all communicators with default settings.

    :param nr_clients: Number of communicators in the group.
    :return: Group of communicator objects.
    """
    return [HttpCommunicator(port=port) for port in ports]


async def _create_pool_group(
    _pool_factory_: PoolFactory, communicators: list[HttpCommunicator]
) -> list[Pool]:
    """
    HTTP pool group initializer.

    Initializes all pools for the group without certificates.
    Does not configure communication.

    :param _pool_factory_: Pool factory.
    :param communicators: Communicators.
    :return: Group of pool objects.
    """
    return [
        await _pool_factory_(f"local{i}", communicator)
        for i, communicator in enumerate(communicators)
    ]


def _configure_clients(pools: Iterable[Pool]) -> None:
    """
    Adds clients to every pool in the group. Configures mutual connection between every pair of
    pools.

    :param pools: Group of pools that are configured with servers.
    """
    for server_pool, (client_nr, client_pool) in itertools.product(
        pools, enumerate(pools)
    ):
        if server_pool == client_pool:
            continue
        assert isinstance(client_pool.communicator, HttpCommunicator)
        connection = HttpConnection(
            addr="localhost",
            port=client_pool.communicator.port,
        )
        server_pool.add_client(f"local{client_nr}", connection)
