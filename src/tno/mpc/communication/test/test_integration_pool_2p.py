"""
This module contains a generic test suite for integration tests between two
communication pools.

The integration test suite is implemented for the MockCommunicator and the
HttpCommunicator.
"""

from __future__ import annotations

import asyncio

import pytest

from tno.mpc.communication import CommunicationError, Pool, Serializer
from tno.mpc.communication.test.serializer_plugins.test_packing import (
    ClassCorrect,
    MyDataClass,
    NestedClassCorrect,
)


class IntegrationTestSuitePool2p:
    """
    Generic test class for integration a set of two communication pools. Each
    test in this class expects a tuple of two communication pools which have
    been initialized.

    :see: :class:`IntegrationTestSuiteHttpPool2p`
    :see: :class:`IntegrationTestSuiteMockPool2p`
    """

    @pytest.mark.asyncio
    async def test_send_recv_single_msg(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of a message between two communication pools.

        :param pools: Collection of two communication pools
        """
        await pools[0].send("local1", "Hello!")
        res = await pools[1].recv("local0")
        assert res == "Hello!"

    @pytest.mark.asyncio
    async def test_send_recv_single_msg_with_msg_id(
        self, pools: tuple[Pool, Pool]
    ) -> None:
        """
        Tests sending and receiving of a message between two communication pools.

        :param pools: Collection of two communication pools
        """
        await pools[0].send("local1", "Hello!", "my_msg_id")
        res = await pools[1].recv("local0", "my_msg_id")
        assert res == "Hello!"

    @pytest.mark.asyncio
    async def test_send_recv_multiple_msg(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of multiple messages between two
        communication pools.

        :param pools: Collection of two communication pools
        """
        await pools[0].send("local1", "Hello1!")
        await pools[0].send("local1", "Hello2!")

        res = await pools[1].recv("local0")
        assert res == "Hello1!"

        res = await pools[1].recv("local0")
        assert res == "Hello2!"

    @pytest.mark.asyncio
    async def test_recv_timeout(self, pools: tuple[Pool, Pool]) -> None:
        """
        Verify that the timeout parameter in pool.recv is respected. Fails if the thread hangs.

        :param pools: Collection of two communication pools.
        """

        async def failing_sender() -> None:
            pass

        async def receiver_with_timeout() -> None:
            await pools[1].recv("local0", timeout=1)

        async def test_attempt_to_communicate() -> None:
            with pytest.raises(CommunicationError):
                await asyncio.gather(failing_sender(), receiver_with_timeout())

        try:
            await asyncio.wait_for(test_attempt_to_communicate(), timeout=2)
        except asyncio.TimeoutError:
            assert False, "Receiving pool thread hangs."

    @pytest.mark.asyncio
    async def test_msg_id_custom(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of an int with a custom message id between
        two communication pools.

        :param pools: Collection of two communication pools.
        """
        await pools[0].send("local1", "Hello!", "my_msg_id")
        res = await pools[1].recv("local0", "my_msg_id")
        assert res == "Hello!"

    @pytest.mark.asyncio
    async def test_serialization_int(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of an integer between two communication pools.

        :param pools: Collection of two communication pools.
        """
        await pools[0].send("local1", 1234)
        res = await pools[1].recv("local0")
        assert isinstance(res, int)
        assert res == 1234

    @pytest.mark.asyncio
    async def test_serialization_float(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of a float between two communication pools.

        :param pools: Collection of two communication pools.
        """
        await pools[0].send("local1", 1234.4321)
        res = await pools[1].recv("local0")
        assert isinstance(res, float)
        assert res == 1234.4321

    @pytest.mark.asyncio
    async def test_serialization_bytes(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of a bytes object between two communication pools.

        :param pools: Collection of two communication pools.
        """
        await pools[0].send("local1", b"Hello!")
        res = await pools[1].recv("local0")
        assert isinstance(res, bytes)
        assert res == b"Hello!"

    @pytest.mark.asyncio
    async def test_serialization_list(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of a list between two communication pools.

        :param pools: Collection of two communication pools.
        """
        list_ = [1, 2, 3, 4]
        await pools[0].send("local1", list_)
        res = await pools[1].recv("local0")
        assert isinstance(res, list)
        assert res == list_

    @pytest.mark.asyncio
    async def test_serialization_collection(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of a dictionary between two communication pools.

        :param pools: Collection of two communication pools.
        """
        collection = {"1": 1, "2": 2}
        await pools[0].send("local1", collection)
        res = await pools[1].recv("local0")
        assert isinstance(collection, type(res))
        assert res == collection

    @pytest.mark.asyncio
    async def test_serialization_string(self, pools: tuple[Pool, Pool]) -> None:
        """
        Tests sending and receiving of a string between two communication pools.

        :param pools: Collection of two communication pools.
        """
        await pools[0].send("local1", "Hello!")
        res = await pools[1].recv("local0")
        assert isinstance(res, str)
        assert res == "Hello!"

    @pytest.mark.asyncio
    async def test_serialization_nested_custom_object(
        self, pools: tuple[Pool, Pool]
    ) -> None:
        """
        Tests sending and receiving of a object with nested, custom serialization
        between two communication pools.

        :param pools: Collection of two communication pools.
        """
        Serializer.register_class(ClassCorrect)
        Serializer.register_class(MyDataClass)
        Serializer.register_class(NestedClassCorrect)
        my_obj = NestedClassCorrect(ClassCorrect(1), MyDataClass(1))
        await pools[0].send("local1", my_obj)
        res = await pools[1].recv("local0")
        assert isinstance(res, NestedClassCorrect)
        assert isinstance(res.dataclass, MyDataClass)
        assert isinstance(res.instance, ClassCorrect)
        assert res == my_obj


class TestIntegrationTestSuiteMockPool2p(IntegrationTestSuitePool2p):
    """
    Run the IntegrationTestSuitePool2p tests with Pools initialized with a MockCommunicator.
    """

    @pytest.fixture(name="pools")
    def fixture_pools(self, mock_pool_duo: tuple[Pool, Pool]) -> tuple[Pool, Pool]:
        """
        Fixture returning a tuple of two communication pools initialized with a MockCommunicator.

        :param mock_pool_duo: Fixture returning a tuple of two communication pools initialized with a MockCommunicator.
        :return: Tuple of two communication pools.
        """
        return mock_pool_duo


class TestIntegrationTestSuiteHttpPool2p(IntegrationTestSuitePool2p):
    """
    Run the IntegrationTestSuitePool2p tests with Pools initialized with HttpCommunicator.
    """

    @pytest.fixture(name="pools")
    def fixture_pools(self, http_pool_duo: tuple[Pool, Pool]) -> tuple[Pool, Pool]:
        """
        Fixture returning a tuple of two communication pools initialized with HttpCommunicator.

        :param http_pool_duo: Fixture returning a tuple of two communication pools initialized with HttpCommunicator.
        :return: Tuple of two communication pools.
        """
        return http_pool_duo
