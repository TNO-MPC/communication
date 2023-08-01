"""
Validates that the pytest plugins work as expected.
"""
# pylint: disable=protected-access
from __future__ import annotations

import asyncio
from typing import Collection

import pytest
from aiohttp import web

from tno.mpc.communication import Pool


@pytest.mark.asyncio
async def test_generated_pool_group_reuses_ports(
    http_pool_duo: Collection[Pool],
) -> None:
    """
    Ensure that generated TCPSites allow reuse of ports. This prevents port allocation conflicts.

    :param http_pool_duo: collection of two communication pools
    """
    await asyncio.gather(*(pool.http_server.server_task for pool in http_pool_duo))  # type: ignore[union-attr]
    assert all(pool.http_server.site._reuse_port for pool in http_pool_duo)  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_reuse_pool_monkeypatch_limited_to_test_setup(
    http_pool_duo: tuple[Pool, Pool]
) -> None:
    """
    Verify that the patching of aiohttp.web.TCPSite is undone after the pools are created.

    :param http_pool_duo: collection of two communication pools
    """
    app = web.Application(client_max_size=0)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner=runner)

    assert http_pool_duo[0].http_server.site._reuse_port  # type: ignore[union-attr]
    assert not site._reuse_port
