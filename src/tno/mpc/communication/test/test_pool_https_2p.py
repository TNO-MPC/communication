"""
This module tests the communication between three communication pools with SSL enabled
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable

import pytest
import pytest_asyncio
from aiohttp import ClientConnectorCertificateError

from pytest_tno.tno.mpc.communication.pytest_pool_fixtures import get_available_ports
from tno.mpc.communication import Pool
from tno.mpc.communication.test.conftest import TEST_CERTIFICATE_DIR
from tno.mpc.communication.test.test_pool_http_3p import assert_send_message

CERT_TRUSTED_SERVER = {
    "key": TEST_CERTIFICATE_DIR / "party_0.pem",
    "cert": TEST_CERTIFICATE_DIR / "party_0.crt",
    "ca_cert": TEST_CERTIFICATE_DIR / "ca-combined.crt",
}
CERT_TRUSTED_CLIENT = {
    "key": TEST_CERTIFICATE_DIR / "party_1.pem",
    "cert": TEST_CERTIFICATE_DIR / "party_1.crt",
    "ca_cert": TEST_CERTIFICATE_DIR / "ca-combined.crt",
}
CERT_UNTRUSTED = {
    "key": TEST_CERTIFICATE_DIR / "party_untrusted.pem",
    "cert": TEST_CERTIFICATE_DIR / "party_untrusted.crt",
    "ca_cert": TEST_CERTIFICATE_DIR / "ca-untrusted.crt",
}


@pytest_asyncio.fixture(name="_pool_factory", scope="function")
async def fixture_pool_factory_function_scope() -> AsyncIterator[Callable[..., Pool]]:
    """
    Factory of pool objects. Ensures proper shutdown afterwards.

    Fixture scope is explicitly limited to "function".

    :return: Factory function for a single pool object.
    """
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


@pytest.mark.asyncio
async def test_https_pool_no_mutual_tls_delivers_messages(
    _pool_factory: Callable[..., Pool],
) -> None:
    """
    Tests sending and receiving of multiple messages between two communication pools using SSL/TLS
    verification of the server only.

    :param _pool_factory: Pool factory fixture.
    """
    sender = _pool_factory(**CERT_TRUSTED_SERVER)
    receiver = _pool_factory(**CERT_TRUSTED_CLIENT)
    sender_port, receiver_port = get_available_ports(2)
    sender.add_http_server(sender_port)
    receiver.add_http_server(receiver_port)
    sender.add_http_client("local1", "127.0.0.1", receiver_port, cert=None)
    receiver.add_http_client("local0", "127.0.0.1", sender_port, cert=None)

    await assert_send_message((sender, receiver), 0, 1, "Secure hello to you!")
    await assert_send_message((sender, receiver), 1, 0, "Secure hello to you too!")


@pytest.mark.asyncio
async def test_https_pool_with_mutual_tls_delivers_messages(
    _pool_factory: Callable[..., Pool],
) -> None:
    """
    Tests sending and receiving of multiple messages between two communication pools using mutual
    SSL/TLS verification.

    :param _pool_factory: Pool factory fixture.
    """
    sender = _pool_factory(**CERT_TRUSTED_SERVER)
    receiver = _pool_factory(**CERT_TRUSTED_CLIENT)
    sender_port, receiver_port = get_available_ports(2)
    sender.add_http_server(sender_port)
    receiver.add_http_server(receiver_port)
    sender.add_http_client(
        "local1", "127.0.0.1", receiver_port, cert=CERT_TRUSTED_CLIENT["cert"]
    )
    receiver.add_http_client(
        "local0", "127.0.0.1", sender_port, cert=CERT_TRUSTED_SERVER["cert"]
    )

    await assert_send_message((sender, receiver), 0, 1, "Doubly secure hello to you!")
    await assert_send_message(
        (sender, receiver), 1, 0, "Doubly secure hello to you too!"
    )


@pytest.mark.asyncio
async def test_https_pool_fails_if_server_pool_has_unauthorized_certificate(
    _pool_factory: Callable[..., Pool],
) -> None:
    """
    Assert that mutual TLS communication fails if the server's certificate is signed by an unknown
    CA.

    :param _pool_factory: Pool factory fixture.
    """
    sender = _pool_factory(**CERT_UNTRUSTED)
    receiver = _pool_factory(**CERT_TRUSTED_CLIENT)
    sender_port, receiver_port = get_available_ports(2)
    sender.add_http_server(sender_port)
    receiver.add_http_server(receiver_port)
    sender.add_http_client("local1", "127.0.0.1", receiver_port)
    receiver.add_http_client("local0", "127.0.0.1", sender_port)

    with pytest.raises(ClientConnectorCertificateError):
        await assert_send_message(
            (sender, receiver), 0, 1, "Not quite secure hello to you!"
        )


@pytest.mark.asyncio
async def test_https_pool_fails_if_client_pool_has_unauthorized_certificate(
    _pool_factory: Callable[..., Pool],
) -> None:
    """
    Assert that mutual TLS communication fails if the client's certificate is signed by an unknown
    CA.

    :param _pool_factory: Pool factory fixture.
    """
    sender = _pool_factory(**CERT_TRUSTED_SERVER)
    receiver = _pool_factory(**CERT_UNTRUSTED)
    sender_port, receiver_port = get_available_ports(2)
    sender.add_http_server(sender_port)
    receiver.add_http_server(receiver_port)
    sender.add_http_client(
        "local1", "127.0.0.1", receiver_port, cert=CERT_UNTRUSTED["cert"]
    )
    receiver.add_http_client(
        "local0", "127.0.0.1", sender_port, cert=CERT_TRUSTED_SERVER["cert"]
    )

    with pytest.raises(ClientConnectorCertificateError):
        await assert_send_message(
            (sender, receiver), 0, 1, "Not quite secure hello to you!"
        )
