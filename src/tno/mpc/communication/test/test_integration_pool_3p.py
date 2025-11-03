"""
This module tests the communication between three communication pools.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from tno.mpc.communication import Pool
from tno.mpc.communication.test.util import (
    assert_broadcast_message,
    assert_recv_message,
    assert_send_message,
    assert_send_recv_all_message,
    send_message,
)


class IntegrationTestSuitePool3p:
    """
    Generic test class for integration a set of three communication pools. Each
    test in this class expects a tuple of three communication pools which have
    been initialized.

    :see: :class:`IntegrationTestSuiteHttpPool3p`
    :see: :class:`IntegrationTestSuiteMockPool3p`
    """

    @pytest.mark.asyncio
    async def test_send_recv_one(self, pools: tuple[Pool, Pool, Pool]) -> None:
        """
        Tests sending and receiving of multiple messages between three communication pools.

        :param pools: collection of three communication pools
        """
        await asyncio.gather(
            *(
                assert_send_message(pools, 0, 1, "Hello1!"),
                assert_send_message(pools, 0, 2, "Hello2!"),
                assert_send_message(pools, 1, 0, "Hello3!"),
                assert_send_message(pools, 1, 2, "Hello4!"),
                assert_send_message(pools, 2, 0, "Hello5!"),
                assert_send_message(pools, 2, 1, "Hello6!"),
            )
        )

    @pytest.mark.asyncio
    async def test_send_recv_multi(self, pools: tuple[Pool, Pool, Pool]) -> None:
        """
        Tests sending and receiving of multiple messages between three communication pools.

        :param pools: collection of three communication pools
        """
        await asyncio.gather(
            *(
                assert_send_message(pools, 0, 1, "Hello1!", "id1"),
                assert_send_message(pools, 0, 1, "Hello2!", "id2"),
                assert_send_message(pools, 0, 1, "Hello1!", "id3"),
            )
        )

    @pytest.mark.asyncio
    async def test_send_recv_multi_subset(self, pools: tuple[Pool, Pool, Pool]) -> None:
        """
        Tests sending and receiving of multiple broadcast messages between three communication pools.

        :param pools: collection of three communication pools
        """
        await asyncio.gather(
            *(
                assert_broadcast_message(pools, 0, [1, 2], "Hello1!", "id1"),
                assert_broadcast_message(pools, 1, [0, 2], "Hello2!", "id2"),
                assert_broadcast_message(pools, 2, [0, 1], "Hello3!", "id3"),
                assert_broadcast_message(pools, 0, [1], "Hello1!", "id4"),
                assert_broadcast_message(pools, 1, [2], "Hello2!", "id5"),
                assert_broadcast_message(pools, 2, [0], "Hello3!", "id6"),
            )
        )

    @pytest.mark.asyncio
    async def test_broadcast(self, pools: tuple[Pool, Pool, Pool]) -> None:
        """
        Tests sending and receiving of multiple broadcast messages between three communication pools.

        :param pools: collection of three communication pools
        """
        await asyncio.gather(
            *(
                assert_broadcast_message(pools, 0, [1, 2], "Hello1!", "id1"),
                assert_broadcast_message(pools, 0, [1, 2], "Hello2!", "id2"),
                assert_broadcast_message(pools, 0, [1, 2], "Hello3!", "id3"),
                assert_broadcast_message(pools, 0, [1], "Hello1!", "id4"),
                assert_broadcast_message(pools, 0, [2], "Hello2!", "id5"),
            )
        )

    @pytest.mark.asyncio
    async def test_broadcast_multi(self, pools: tuple[Pool, Pool, Pool]) -> None:
        """
        Tests sending and receiving of multiple messages between three communication pools.

        :param pools: collection of three communication pools
        """
        await asyncio.gather(
            *(
                assert_send_message(pools, 0, 1, "Hello1!", msg_id="Round1"),
                assert_send_message(pools, 0, 2, "Hello2!", msg_id="Round1"),
                assert_send_message(pools, 1, 0, "Hello3!", msg_id="Round1"),
                assert_send_message(pools, 1, 2, "Hello4!", msg_id="Round1"),
                assert_send_message(pools, 2, 0, "Hello5!", msg_id="Round1"),
                assert_send_message(pools, 2, 1, "Hello6!", msg_id="Round1"),
                assert_send_message(pools, 0, 1, "Hello7!", msg_id="Round2"),
                assert_send_message(pools, 0, 2, "Hello8!", msg_id="Round2"),
                assert_send_message(pools, 1, 0, "Hello9!", msg_id="Round2"),
                assert_send_message(pools, 1, 2, "Hello10!", msg_id="Round2"),
                assert_send_message(pools, 2, 0, "Hello11!", msg_id="Round2"),
                assert_send_message(pools, 2, 1, "Hello12!", msg_id="Round2"),
            )
        )

    @pytest.mark.asyncio
    async def test_send_recv_mixed(self, pools: tuple[Pool, Pool, Pool]) -> None:
        """
        Tests sending and receiving of multiple messages of varying types between three communication pools.

        :param pools: collection of three communication pools
        """
        await asyncio.gather(
            *(
                send_message(pools, 0, 1, "Hello1!"),
                send_message(pools, 2, 1, b"Hello2!"),
                send_message(pools, 0, 1, b"Hello3!"),
                send_message(pools, 2, 1, "Hello4!"),
                assert_recv_message(pools, 2, 1, b"Hello2!"),
                assert_recv_message(pools, 2, 1, "Hello4!"),
                assert_recv_message(pools, 0, 1, "Hello1!"),
                assert_recv_message(pools, 0, 1, b"Hello3!"),
            )
        )

    @pytest.mark.asyncio
    async def test_recv_all_subset(self, pools: tuple[Pool, Pool, Pool]) -> None:
        """
        Test receiving of a message from each other party using the recv_all method.

        :param pools: collection of three communication pools
        """
        await asyncio.gather(
            *(
                assert_send_recv_all_message(pools, 0, [1, 2], "Hello1!", "id1"),
                assert_send_recv_all_message(pools, 0, [1, 2], b"Hello2!", "id2"),
                assert_send_recv_all_message(pools, 0, [1, 2], b"Hello3!", "id3"),
                assert_send_recv_all_message(pools, 0, [1], "Hello1!", "id4"),
                assert_send_recv_all_message(pools, 0, [2], b"Hello2!", "id5"),
            )
        )

    @pytest.mark.asyncio
    async def test_broadcast_subset(self, pools: tuple[Pool, Pool, Pool]) -> None:
        """
        Tests sending and receiving of multiple broadcast messages of various types between three communication pools.

        :param pools: collection of three communication pools
        """
        await asyncio.gather(
            *(
                assert_broadcast_message(pools, 0, [1, 2], "Hello1!", "id1"),
                assert_broadcast_message(pools, 0, [1, 2], b"Hello2!", "id2"),
                assert_broadcast_message(pools, 0, [1, 2], b"Hello3!", "id3"),
                assert_broadcast_message(pools, 0, [1], "Hello1!", "id4"),
                assert_broadcast_message(pools, 0, [2], b"Hello2!", "id5"),
            )
        )


class TestIntegrationTestSuiteMockPool3p(IntegrationTestSuitePool3p):
    """
    Run the IntegrationTestSuitePool3p tests with Pools initialized with a MockCommunicator.
    """

    @pytest_asyncio.fixture(name="pools")
    async def fixture_pools(
        self, mock_pool_trio: tuple[Pool, Pool, Pool]
    ) -> tuple[Pool, Pool, Pool]:
        """
        Fixture returning a tuple of three communication pools initialized with a MockCommunicator.

        :param mock_pool_trio: Fixture returning a tuple of three communication pools initialized with a MockCommunicator.
        :returns: A tuple of three communication pools initialized with a MockCommunicator.
        """
        return mock_pool_trio


class TestIntegrationTestSuiteHttpPool3p(IntegrationTestSuitePool3p):
    """
    Run the IntegrationTestSuitePool3p tests with Pools initialized with a HttpCommunicator.
    """

    @pytest_asyncio.fixture(name="pools")
    async def fixture_pools(
        self, http_pool_trio: tuple[Pool, Pool, Pool]
    ) -> tuple[Pool, Pool, Pool]:
        """
        Fixture returning a tuple of three communication pools initialized with a HttpCommunicator.

        :param http_pool_trio: Fixture returning a tuple of three communication pools initialized with a HttpCommunicator.
        :returns: A tuple of three communication pools initialized with a HttpCommunicator.
        """
        return http_pool_trio
