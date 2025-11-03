"""
This module is configured as a pytest plugin and thus automatically exposes the
fixtures from the `tno.mpc.communication` package to library users when
installed.

The module defines a custom option, `--fixture-pool-scope`, that allows users
to set the scope of the pool-related fixtures. The default scope is `function`.

This module also hacks the `pytest-asyncio` plugin to ensure that all tests run
in the same event loop as the pool fixtures.
"""

import warnings
from typing import Final, Literal

import pytest

DEFAULT_LOOP_SCOPE = "function"
PYTEST_SCOPES: Final = ["function", "class", "module", "package", "session"]
PYTEST_SCOPES_LITERAL = Literal[  # pylint: disable=invalid-name
    "function",
    "class",
    "module",
    "package",
    "session",
]


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Add option to the pytest parser that allows customization of the pool-related fixtures' scope.

    :param parser: pytest CLI parser configuration.
    """
    group = parser.getgroup("asyncio")
    group.addoption(
        "--fixture-pool-scope",
        type=str,
        choices=PYTEST_SCOPES,
        help="set scope for the tno.mpc.communication pool fixtures, which by default copies asyncio_default_fixture_loop_scope",
    )


def determine_pool_scope(
    fixture_name: str, config: pytest.Config
) -> PYTEST_SCOPES_LITERAL:
    """
    Getter for the scope of all fixtures related to pool objects.

    :param fixture_name: required by pytest.
    :param config: Pytest configuration object.
    :return: Fixture scope.
    """
    del fixture_name
    return config.getoption("--fixture-pool-scope") or config.getini("asyncio_default_fixture_loop_scope") or DEFAULT_LOOP_SCOPE  # type: ignore[return-value]


try:
    from pytest_tno.tno.mpc.communication.pytest_pool_http_fixtures import *  # noqa: F401 # pylint: disable=unused-wildcard-import,wildcard-import
    from pytest_tno.tno.mpc.communication.pytest_pool_mock_fixtures import *  # noqa: F401 # pylint: disable=unused-wildcard-import,wildcard-import

    def pytest_configure(config: pytest.Config) -> None:
        """
        Configure our pytest_tno plugin. Checks whether the pytest-asyncio loop scopes
        are set appropriately.

        The `pytest-asyncio` library has creates an `event_loop` per scope. This
        gives us trouble as we want to have the pool fixtures to have a large scope
        (i.e. session), yet have the tests run in small scopes (i.e. function,
        which is the default for tests). Thus, when a default test requests
        a session-scope fixture, the fixture will have been initialized on
        a different event-loop (the session-scoped loop) than it is used on (once
        in the test, the running event loop is the function-scoped loop).

        Unfortunately, `aiohttp` doesn't handle this well, as
        `aiohttp.ClientSession` keeps a reference to the event_loop upon creation
        under `self._loop`. Thus once the `ClientSession` is invoked in a test, the
        running event loop is not equal to the referenced loop, and the library
        throws an error.

        Therefore, we enforce the default asyncio fixture and test loop scopes to be
        identical (see `pyproject.toml`), and that the `--fixture-pool-scope` (from `pytest_tno`) scope is not
        larger.
        """
        fixture_loop_scope_option = (
            config.getini("asyncio_default_fixture_loop_scope") or DEFAULT_LOOP_SCOPE
        )
        test_loop_scope_option = (
            config.getini("asyncio_default_test_loop_scope") or DEFAULT_LOOP_SCOPE
        )

        if fixture_loop_scope_option != test_loop_scope_option:
            warnings.warn(
                "The value of the option `asyncio_default_fixture_loop_scope` "
                f"({test_loop_scope_option}) is different from the value of the option "
                f"`asyncio_default_test_loop_scope` ({fixture_loop_scope_option}). This "
                "will very likely cause issues when using the `tno.mpc.communication` "
                "fixtures."
            )

        pytest_tno_pool_fixture_scope = determine_pool_scope("", config)
        if PYTEST_SCOPES.index(pytest_tno_pool_fixture_scope) > PYTEST_SCOPES.index(
            fixture_loop_scope_option
        ):
            warnings.warn(
                "The scope provided through the option `--fixture-pool-scope` "
                f"({pytest_tno_pool_fixture_scope}) is larger then the scope of "
                f"`asyncio_default_test_loop_scope` ({fixture_loop_scope_option}). This "
                "will very likely cause issues when using the `tno.mpc.communication` "
                "fixtures."
            )

        warnings.warn(
            "The `tno.mpc.communication` fixtures set an infinite timeout for "
            "awaiting messages through a Pool. This is to prevent tests from "
            "hanging on slow CI/CD pipelines. To reproduce this behavior "
            "locally, set `Pool(..., timeout=None)`."
        )

except ImportError:
    warnings.warn(
        "Failed to import the dependencies for the 'tno.mpc.communication' fixtures. If you require these fixtures, please install `tno.mpc.communication[pytest]`."
    )
