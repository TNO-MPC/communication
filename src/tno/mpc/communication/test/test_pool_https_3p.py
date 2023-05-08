"""
This module tests the communication between three communication pools with SSL enabled
"""
from typing import Tuple

import pytest

from tno.mpc.communication import Pool
from tno.mpc.communication.test import (  # pylint: disable=unused-import
    fixture_pool_https_3p,
    fixture_pool_https_3p_certs_as_id,
)
from tno.mpc.communication.test.test_pool_http_3p import assert_send_message


@pytest.mark.asyncio
async def test_https_3p_server(pool_https_3p: Tuple[Pool, Pool, Pool]) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools using SSL/TLS

    :param pool_https_3p: collection of three communication pools
    """
    await assert_send_message(pool_https_3p, 0, 1, "Hello1!")
    await assert_send_message(pool_https_3p, 0, 2, "Hello2!")
    await assert_send_message(pool_https_3p, 1, 0, "Hello3!")
    await assert_send_message(pool_https_3p, 1, 2, "Hello4!")
    await assert_send_message(pool_https_3p, 2, 0, "Hello5!")
    await assert_send_message(pool_https_3p, 2, 1, "Hello6!")


@pytest.mark.asyncio
async def test_https_3p_server_with_certs_as_identification(
    pool_https_3p_certs_as_id: Tuple[Pool, Pool, Pool]
) -> None:
    """
    Tests sending and receiving of multiple messages between three communication pools using SSL/TLS

    :param pool_https_3p_certs_as_id: collection of three communication pools
    """
    await assert_send_message(pool_https_3p_certs_as_id, 0, 1, "Hello1!")
    await assert_send_message(pool_https_3p_certs_as_id, 0, 2, "Hello2!")
    await assert_send_message(pool_https_3p_certs_as_id, 1, 0, "Hello3!")
    await assert_send_message(pool_https_3p_certs_as_id, 1, 2, "Hello4!")
    await assert_send_message(pool_https_3p_certs_as_id, 2, 0, "Hello5!")
    await assert_send_message(pool_https_3p_certs_as_id, 2, 1, "Hello6!")
