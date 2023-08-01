"""
Pytest fixtures for generating groups of pools.
"""
# pylint: disable=import-outside-toplevel  # toplevel import messes up coverage results
from __future__ import annotations

import asyncio
import contextlib
import itertools
from asyncio import AbstractEventLoop
from functools import lru_cache, partial
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Collection,
    ContextManager,
    Final,
    Iterator,
    List,
    Literal,
    cast,
)

import aiohttp
import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from tno.mpc.communication import Pool
    from tno.mpc.communication.httphandlers import HTTPServer

    PoolFactory = Callable[..., Pool]
    PoolGroupFactory = Callable[[PoolFactory, int], List[Pool]]

DEFAULT_POOL_SCOPE = "function"
PYTEST_SCOPES: Final = ["function", "class", "module", "package", "session"]
PYTEST_SCOPES_LITERAL = Literal[  # pylint: disable=invalid-name
    "function", "class", "module", "package", "session"
]


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Add option to the pytest parser that allows customization of the pool-related fixtures' scope.

    :param parser: pytest CLI parser configuration.
    """
    group = parser.getgroup("asyncio")
    group.addoption(
        "--fixture-pool-scope",
        default=DEFAULT_POOL_SCOPE,
        type=str,
        choices=PYTEST_SCOPES,
        help="set scope for the tno.mpc.communication pool and asyncio event_loop fixtures",
    )


def pytest_plugin_registered(  # pylint: disable=unused-argument  # required arguments to pytest hook
    plugin: Any, manager: pytest.PytestPluginManager
) -> None:
    """
    Overwrite the pytest-asyncio event loop with a dynamically-scoped event loop.

    The logic in pytest-asyncio heavily relies on the assumption that a fixture with the name
    "event_loop" provides an event loop (and injects that fixture dynamically to test definitions).
    As such, our dynamically-scoped fixture "event_loop" competes with the pytest_asyncio
    "event_loop" and we explicitly overwrite it.

    :param plugin: Plugin module or instance.
    :param manager: pytest plugin manager.
    """
    # Both our and pytest_asyncio's "event_loop" are consulted last by pytest
    # (https://docs.pytest.org/en/stable/reference/fixtures.html#fixtures-from-third-party-plugins)
    # and pytest prefers the "event_loop" of pytest_asyncio (possibly due to the lower scope;
    # https://docs.pytest.org/en/stable/reference/fixtures.html#higher-scoped-fixtures-are-executed-first,
    # or because of some intricacies in the the pytest_asyncio module).
    setattr(pytest_asyncio.plugin, "event_loop", event_loop)


def determine_pool_scope(
    fixture_name: str, config: pytest.Config
) -> PYTEST_SCOPES_LITERAL:
    """
    Getter for the scope of all fixtures related to pool objects. This includes the event loop
    fixture.

    :param fixture_name: required by pytest.
    :param config: Pytest configuration object.
    :return: Fixture scope.
    """
    del fixture_name
    return config.getoption("--fixture-pool-scope")  # type: ignore[no-any-return]


@pytest.fixture(scope=determine_pool_scope)
def event_loop(  # pylint: disable=unused-argument
    request: pytest.FixtureRequest,
) -> Iterator[AbstractEventLoop]:
    """
    Create an instance of the default event loop. This overrides the event_loop method from
    pytest-asyncio with a custom scope. The scope is set according to the globally configured scope
    (--fixture-pool-scope).

    :param request: A fixture request.
    :return: A new event loop.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope=determine_pool_scope)
def http_pool_duo(
    http_pool_group_factory: Callable[[int], tuple[Pool, ...]]
) -> tuple[Pool, Pool]:
    """
    Two communication pools without TLS/SSL.

    :param http_pool_group_factory: factory for creating a HTTP pool group.
    :return: Two communication pools without TLS/SSL.
    """
    return http_pool_group_factory(2)  # type: ignore[return-value]


@pytest.fixture(scope=determine_pool_scope)
def http_pool_trio(
    http_pool_group_factory: Callable[[int], tuple[Pool, ...]]
) -> tuple[Pool, Pool, Pool]:
    """
    Three communication pools without TLS/SSL.

    :param http_pool_group_factory: factory for creating a HTTP pool group.
    :return: Three communication pools without TLS/SSL.
    """
    return http_pool_group_factory(3)  # type: ignore[return-value]


@pytest.fixture(name="http_pool_group_factory", scope=determine_pool_scope)
def fixture_http_pool_group_factory(
    _pool_factory: PoolFactory,
    _enable_port_reuse: Callable[[], ContextManager[None]],
) -> Callable[[int], tuple[Pool, ...]]:
    """
    Factory for creating a HTTP pool group with the requested number of pools.

    The pool group is configured without SSL certificates.

    :return: Factory for creating a HTTP pool group with the requested number of pools.
    """

    @lru_cache
    def tno_communication_pool_group(n_pools: int) -> tuple[Pool, ...]:
        """
        Factory for creating a HTTP pool group with the requested number of pools.

        :param n_pools: Number of pools in the group.
        :return: Group of pool objects with mutual communication configured.
        """
        with _enable_port_reuse():
            return _generate_test_pools(
                n_pools,
                _pool_factory_=_pool_factory,
            )

    return tno_communication_pool_group


def _generate_test_pools(
    nr_clients: int,
    _pool_factory_: PoolFactory,
) -> tuple[Pool, ...]:
    """
    Generates a group of communication pools and sets up the communication between them.

    :param nr_clients: Number of pools in the group.
    :param _pool_factory_: Factory of pool objects.
    :raise ValueError: If the number of clients exceeds nine.
    :return: Fully initialized pools.
    """
    if nr_clients < 1 or nr_clients > 9:
        raise ValueError(
            f"The test pool generator can create pool groups with 1-9 clients, but {nr_clients} clients were requested."
        )
    pools = _init_pool_group(_pool_factory_, nr_clients)
    _configure_servers(pools)
    _configure_clients(pools)
    return tuple(pools)


def _init_pool_group(_pool_factory_: PoolFactory, nr_clients: int) -> list[Pool]:
    """
    HTTP pool group initializer.

    Initializes all pools for the group without certificates.
    Does not configure communication.

    :param _pool_factory_: Pool factory.
    :param nr_clients: Number of pools in the group.
    :return: Group of pool objects.
    """
    return [_pool_factory_() for _ in range(nr_clients)]


def _configure_servers(pools: Collection[Pool]) -> None:
    """
    Adds a server to every pool.

    If there are n pools in the group, then pool listens on port 4444 + 10 * n + i. Thus, in a
    group with two pools, pool 0 listens on port 4464 and pool 1 listens on port 4465.

    :param pools: Pools that need a server.
    """
    nr_clients = len(pools)
    port_offset = 4444 + nr_clients * 10
    for pool_nr, pool in enumerate(pools):
        pool.add_http_server(port=port_offset + pool_nr)


def _configure_clients(pools: Collection[Pool]) -> None:
    """
    Adds clients to every pool in the group. Configures mutual connection between every pair of
    pools.

    :param pools: Group of pools that are configured with servers.
    """
    from tno.mpc.communication.httphandlers import HTTPServer

    for server_pool, (client_nr, client_pool) in itertools.product(
        pools, enumerate(pools)
    ):
        if server_pool == client_pool:
            continue
        server_pool.add_http_client(
            name=f"local{client_nr}",
            addr="127.0.0.1",
            port=cast(HTTPServer, client_pool.http_server).port,
            cert=client_pool.cert,
        )


@pytest.fixture(scope=determine_pool_scope)
def _enable_port_reuse() -> Callable[[], ContextManager[None]]:
    """
    Provides context manager that enables re-use of HTTP ports. Avoids port allocation conflicts
    between successive generations of pool fixtures.

    More specifically, we avoid "Address already in use" exceptions caused by attempting to
    connect to ports that have not yet been freed between e.g. two calls to the
    `https_pool_duo_mutual_tls` fixture when it's scope is limited.

    :return: Contextmanager for environment where aiohttp.web.TCPSite is always generated with
        'reuse_port=True'.
    """

    @contextlib.contextmanager
    def _enable_port_reuse_cm() -> Iterator[None]:
        """
        Context manager that enables re-use of HTTP ports. Avoids port allocation conflicts
        between successive generations of pool fixtures.

        :return: Context manager.
        """
        new_tcpsite = partial(aiohttp.web.TCPSite, reuse_port=True)
        with pytest.MonkeyPatch.context() as mpatched:
            mpatched.setattr(aiohttp.web, "TCPSite", new_tcpsite)
            yield

    return _enable_port_reuse_cm


@pytest_asyncio.fixture(name="_pool_factory", scope=determine_pool_scope)
async def _fixture_pool_factory() -> AsyncIterator[PoolFactory]:
    """
    Factory of pool objects. Ensures proper shutdown afterwards.

    :return: Factory function for a single pool object.
    """
    from tno.mpc.communication import Pool

    pools: list[Pool] = []

    def pool_creator(*args: Any, **kwargs: Any) -> Pool:
        r"""
        Create a Pool with the provided arguments.

        :param \*args: Positional arguments to Pool.
        :param \**kwargs: Keyword arguments to Pool.
        :return: Instantiated Pool.
        """
        pool = Pool(*args, **kwargs)
        pools.append(pool)
        return pool

    yield pool_creator

    for pool in pools:
        await pool.shutdown()
