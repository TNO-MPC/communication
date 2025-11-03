"""
This module tests the communication between three communication pools with SSL enabled
"""

# pylint: disable=useless-param-doc

from __future__ import annotations

import ssl
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Callable, cast

import pytest
import pytest_asyncio
from aiohttp import ClientConnectorCertificateError

from tno.mpc.communication import HttpCommunicator, HttpConnection, Pool
from tno.mpc.communication.test.util import TEST_CERTIFICATE_DIR, assert_send_message

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


def create_ssl_context(
    key: Path | str, cert: Path | str, ca_cert: Path | str
) -> tuple[ssl.SSLContext, ssl.SSLContext]:
    """
    Initialize a server SSLContext and a client SSLContext, with a custom
    Certificate Authority.

    The key and certificate paths are provided as arguments to ssl.SSLContext.load_cert_chain.
    The ca_cert is provided as argument to ssl.SSLContext.load_verify_locations. Please refer
    to https://docs.python.org/3/library/ssl.html#certificates to learn more about the expected
    files and their format.

    :param key: Path to the key to use in the ssl context.
    :param cert: Path to the certificate to use in the ssl context.
    :param ca_cert: Path to the certificate authority (CA) certificate to use
        in the ssl context
    :return: A tuple of two ssl.SSLContext, the first being the server context
        intended for use in the HTTP Server and the second being the client
        context intended to be used for HTTP Client requests, and the second
    """

    def _create_with_purpose(purpose: ssl.Purpose) -> ssl.SSLContext:
        ctx = ssl.create_default_context(purpose=purpose)
        ctx.load_cert_chain(certfile=cast(str, cert), keyfile=cast(str, key))
        ctx.load_verify_locations(cafile=ca_cert)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_REQUIRED
        return ctx

    client_context = _create_with_purpose(ssl.Purpose.SERVER_AUTH)
    server_context = _create_with_purpose(ssl.Purpose.CLIENT_AUTH)

    return (
        server_context,
        client_context,
    )


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
        communicator = HttpCommunicator(*args, **kwargs)
        pool = Pool(f"local{len(pools)}", communicator)
        pools.append(pool)
        return pool

    yield pool_creator

    for pool in pools:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_https_pool_with_mutual_tls_delivers_messages(
    _pool_factory: Callable[..., Pool],
    unused_tcp_port_factory: Callable[[], int],
) -> None:
    """
    Tests sending and receiving of multiple messages between two communication pools using mutual
    SSL/TLS verification.

    :param _pool_factory: Pool factory fixture.
    :param unused_tcp_port_factory: pytest_asyncio fixture for getting unused tcp_ports.
    """
    sender_port, receiver_port = (unused_tcp_port_factory() for _ in range(2))
    send_server_ctx, send_client_ctx = create_ssl_context(**CERT_TRUSTED_SERVER)
    recv_server_ctx, recv_client_ctx = create_ssl_context(**CERT_TRUSTED_CLIENT)
    sender = _pool_factory(
        port=sender_port,
        ssl_server_context=send_server_ctx,
        ssl_client_context=send_client_ctx,
    )
    receiver = _pool_factory(
        port=receiver_port,
        ssl_server_context=recv_server_ctx,
        ssl_client_context=recv_client_ctx,
    )
    sender.add_client(
        "local1",
        HttpConnection("localhost", receiver_port, cert=CERT_TRUSTED_CLIENT["cert"]),
    )
    receiver.add_client(
        "local0",
        HttpConnection("localhost", sender_port, cert=CERT_TRUSTED_SERVER["cert"]),
    )
    await sender.initialize()
    await receiver.initialize()

    await assert_send_message((sender, receiver), 0, 1, "Doubly secure hello to you!")
    await assert_send_message(
        (sender, receiver), 1, 0, "Doubly secure hello to you too!"
    )


@pytest.mark.asyncio
async def test_https_pool_fails_if_server_pool_has_unauthorized_certificate(
    _pool_factory: Callable[..., Pool],
    unused_tcp_port_factory: Callable[[], int],
) -> None:
    """
    Assert that mutual TLS communication fails if the server's certificate is signed by an unknown
    CA.

    :param _pool_factory: Pool factory fixture.
    :param unused_tcp_port_factory: pytest_asyncio fixture for getting unused tcp_ports.
    """
    sender_port, receiver_port = (unused_tcp_port_factory() for _ in range(2))

    send_server_ctx, send_client_ctx = create_ssl_context(**CERT_UNTRUSTED)
    recv_server_ctx, recv_client_ctx = create_ssl_context(**CERT_TRUSTED_SERVER)
    sender = _pool_factory(
        port=sender_port,
        ssl_server_context=send_server_ctx,
        ssl_client_context=send_client_ctx,
    )
    receiver = _pool_factory(
        port=receiver_port,
        ssl_server_context=recv_server_ctx,
        ssl_client_context=recv_client_ctx,
    )
    sender.add_client("local1", HttpConnection("localhost", receiver_port))
    receiver.add_client("local0", HttpConnection("localhost", sender_port))
    await sender.initialize()
    await receiver.initialize()

    with pytest.raises(ClientConnectorCertificateError):
        await assert_send_message(
            (sender, receiver), 0, 1, "Not quite secure hello to you!"
        )


@pytest.mark.asyncio
async def test_https_pool_fails_if_client_pool_has_unauthorized_certificate(
    _pool_factory: Callable[..., Pool],
    unused_tcp_port_factory: Callable[[], int],
) -> None:
    """
    Assert that mutual TLS communication fails if the client's certificate is signed by an unknown
    CA.

    :param _pool_factory: Pool factory fixture.
    :param unused_tcp_port_factory: pytest_asyncio fixture for getting unused tcp_ports.
    """
    sender_port, receiver_port = (unused_tcp_port_factory() for _ in range(2))
    send_server_ctx, send_client_ctx = create_ssl_context(**CERT_TRUSTED_SERVER)
    recv_server_ctx, recv_client_ctx = create_ssl_context(**CERT_UNTRUSTED)
    sender = _pool_factory(
        port=sender_port,
        ssl_server_context=send_server_ctx,
        ssl_client_context=send_client_ctx,
    )
    receiver = _pool_factory(
        port=receiver_port,
        ssl_server_context=recv_server_ctx,
        ssl_client_context=recv_client_ctx,
    )
    sender.add_client(
        "local1",
        HttpConnection("localhost", receiver_port, cert=CERT_UNTRUSTED["cert"]),
    )
    receiver.add_client(
        "local0",
        HttpConnection("localhost", sender_port, cert=CERT_TRUSTED_SERVER["cert"]),
    )
    await sender.initialize()
    await receiver.initialize()

    with pytest.raises(ClientConnectorCertificateError):
        await assert_send_message(
            (sender, receiver), 0, 1, "Not quite secure hello to you!"
        )
