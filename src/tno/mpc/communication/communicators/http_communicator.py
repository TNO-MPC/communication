"""
Implementation of the Communicator using HTTP servers.
"""

from __future__ import annotations

import logging
import socket
import ssl
import sys
from asyncio import Transport
from pathlib import Path
from typing import Any, cast

from aiohttp import (
    ClientConnectionError,
    ClientSession,
    ClientSSLError,
    ClientTimeout,
    web,
)
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from tno.mpc.communication.communicators.communicator import Communicator
from tno.mpc.communication.exceptions import CommunicationError

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

logger = logging.getLogger(__name__)


class HttpConnection:
    """
    An HttpConnection represents a single point-to-point connection between
    us (the local `Communicator`) and a remote Communicator.
    """

    def __init__(
        self,
        addr: str,
        port: int,
        cert: Path | str | None = None,
        cert_type: int | None = None,
    ):
        """
        Initialize a new `HttpConnection`, representing the connection
        between us and exactly one other `Communicator`.

        The `network_id` is automatically determined based on the
        configuration. The `network_id` is used to associate traffic with the
        correct `Connection`.

        The lifecycle of `HttpConnection` is handled through
        `HttpConnection.setup` and `HttpConnection.close`
        (call upon creation and deletion).

        The `HttpConnection` exposes a `HttpConnection.session` which can
        be used to create HTTP requests for the HTTP server associated with the
        remote. The session object manages the required HTTP connections.

        :param addr: The address of the remote Communicator.
        :param port: The port of the remote Communicator.
        :param cert: The path to the public key of the remote Communicator.
        :param cert_type: The type of the certificate.
        """
        self.addr = addr
        self.port = port
        self.cert = cert
        self.cert_type = cert_type

        self._network_id = self._determine_network_id()
        self._session: ClientSession | None = None

    def _determine_network_id(self) -> str:
        """
        Automatically generates a network identifier, which is used to
        associate HTTP traffic to this `HttpConnection`.

        The network identifier is derived from the SSL Certificate, or from the
        hostname and port if SSL is not enabled.

        :return: The network identifier of this connection.
        """
        if not self.cert:
            return f"{socket.gethostbyname(self.addr)}:{self.port}"

        try:
            import OpenSSL.crypto  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "Could not import the required dependencies for client identification through "
                "ssl/tls. Please install tno.mpc.communication[tls]."
            ) from exc

        with open(self.cert, "rb") as cert_handle:
            client_cert = OpenSSL.crypto.load_certificate(
                self.cert_type or OpenSSL.crypto.FILETYPE_PEM,
                cert_handle.read(),
            )
        return f"{client_cert.get_issuer().CN}:{client_cert.get_serial_number()}"

    @property
    def network_id(self) -> str:
        """
        Returns the network identifier of this `Connection`.

        The network identifier is used to associate HTTP traffic with this
        `Connection`.

        :return: The network identifier of this `Connection`.
        """
        return self._network_id

    @property
    def session(self) -> ClientSession:
        """
        Returns the `aiohttp.ClientSession` object associated with this
        `Connection`.

        The `ClientSession` manages the HTTP connections created while making
        requests to the client via the `Connection`.

        :raise AttributeError: if the `ClientSession` has not yet been created.
        :return: The `ClientSession` associated with this `Connection`.
        """
        if self._session is None:
            raise AttributeError("Client session has not been set.")
        return self._session

    async def setup(self, server_port: int) -> None:
        """
        Setup the connection.

        This method creates a new `aiohttp.ClientSession` object to be used for
        sending HTTP requests to the server of the client. The session takes
        care of efficiently and correctly handling the HTTP connections.

        Note: An event_loop *must* be running when calling this function. This
        is a requirement imposed by `aiohttp.ClientSession`. For this reason,
        this method is asynchronous.

        :param server_port: The port of "our" server under which we are known
            to remotes.
        """
        self._session = ClientSession(
            cookies={"server_port": str(server_port)},
        )

    async def close(self) -> None:
        """
        Close the connection
        """
        await self.session.close()

    def __str__(self) -> str:
        """
        String representation of Self.
        """
        return f"HttpConnection(addr={self.addr}, port={self.port})"


class HttpCommunicator(Communicator[HttpConnection]):
    """
    The HttpCommunicator implements a `Communicator` over HTTP. It provides
    basic capabilities to send and receive bytes to other HttpCommunicators.

    The implementation works as follows. Each `HttpCommunicator` has an HTTP
    server running to which messages can be sent from other `Communicators` by
    sending HTTP POST request to the server.
    """

    def __init__(
        self,
        addr: str = "localhost",
        port: int | None = 80,
        ssl_client_context: ssl.SSLContext | None = None,
        ssl_server_context: ssl.SSLContext | None = None,
        conn_timeout: ClientTimeout = ClientTimeout(total=300),
        conn_retry_max: int = 3,
        conn_retry_delay: int = 1,
    ):
        """
        Initialises the HttpCommunicator with server information and other
        specifications.

        **SSL Configuration**
        One can choose to configure SSL by providing a ssl_client_context and ssl_server_context. Neither or both must be provided.

        The `ssl_client_context` is used by this Communicator to certify itself
        to an HTTP server (another Communicator) when it sends messages. This
        should be an SSLContext with purpose `SERVER_AUTH`. Such a context has
        the property `verify_mode = CERT_REQUIRED` by default, meaning that it
        requires the server to have a (valid) certificate. The context uses our
        provided CA certificate to validate the server
        certificate. Additionally, it uses our provided certificate to
        authenticate us to the server (which may or may not be required by the
        server).

        The `ssl_server_context` is used by the HTTP server started by this
        Communicator to certify itself to clients. This SSLContext should have
        the purpose `CLIENT_AUTH`. *By default, this context does not require
        client authentication*. **You probably want to change this to
        `verify_mode = CERT_REQUIRED`, to ensure mutual TLS**.

        :param addr: The server host address.
        :param port: Optional specification of the server port.
        :param ssl_client_context: The SSLContext to use for HTTP requests made
            by this Communicator as a client.
        :param ssl_server_context: The SSLContext to use for the HTTP server
            started by this Communicator.
        :param conn_timeout: Default timeout for client connections. Defaults to 300s
        :param conn_retry_max: Default maximum number of retries for sending a message
        :param conn_retry_delay: number of seconds to wait before retrying after failure (default is 1s)
        """
        super().__init__()

        # Server configuration
        self.addr = addr
        self.use_ssl = False
        self.ssl_server_context: ssl.SSLContext | None = ssl_server_context
        self.ssl_client_context: ssl.SSLContext | None = ssl_client_context
        self.use_ssl = (self.ssl_client_context or self.ssl_server_context) is not None
        self.port = port or (443 if self.use_ssl else 80)

        # Parameters
        self.conn_timeout = conn_timeout
        self.conn_retry_max = conn_retry_max
        self.conn_retry_delay = conn_retry_delay

        # State
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

        # Optional SSL Configuration
        if self.use_ssl and not (self.ssl_client_context and self.ssl_server_context):
            raise ValueError(
                "You must provide both the client and server SSL contexts when using SSL."
            )

    @override
    async def _initialize(self) -> None:
        # Specify HTTP endpoints
        app = web.Application(client_max_size=0)
        app.router.add_post("/{tail:.*}", self._post_handler)
        app.router.add_get("/{tail:.*}", self._get_handler)

        # Setup runner
        self._runner = web.AppRunner(app)
        await self._runner.setup()

        # Setup site and start serving
        kwargs: dict[str, Any] = {"host": self.addr, "port": self.port}
        kwargs = kwargs | (
            self.use_ssl and {"ssl_context": self.ssl_server_context} or {}
        )
        self._site = web.TCPSite(self._runner, **kwargs)

        await self._site.start()
        logger.info(
            f"Serving on {self.addr}:{str(self.port)}{self.use_ssl and ' with TLS' or ''}"
        )

        # Setup the connections
        for connection in self._connections.values():
            await connection.setup(self.port)

    @override
    async def _send(self, recipient: HttpConnection, packet: bytes) -> None:
        """
        Send a packet of bytes to the specified recipient.

        Sends a POST request containing the provided data to the client. If
        sending of message fails and `self.retry_max != 0` then retry after
        `self.retry_delay` seconds.

        :param recipient: The recipient of the message.
        :param packet: The packet to send to the recipient.
        :raise KeyError: If no client is registered with the given name
            `recipient`.
        """
        logger.debug(f"Sending {len(packet)} bytes to {recipient.network_id}...")
        retryer = AsyncRetrying(
            stop=stop_after_attempt(self.conn_retry_max),
            wait=wait_fixed(self.conn_retry_delay),
            before_sleep=lambda _: logger.debug("Could not connect, retrying..."),
            reraise=False,
            retry=retry_if_exception_type(ClientConnectionError)
            & retry_if_not_exception_type(ClientSSLError),
            # See: https://docs.aiohttp.org/en/stable/client_reference.html#hierarchy-of-exceptions
        )

        try:
            try:
                await retryer(self._try_send, recipient, packet)
            except RetryError as e:
                # Raise underlying exception
                e.reraise()
        except ClientSSLError as e:
            # ClientSSLError is a subclass of ClientConnectionError,
            # but in this case we just want to reraise directly,
            # as its more likely a configuration error than a network error
            raise e
        except ClientConnectionError as e:
            # Configuration is valid, but cannot reach client
            # Configuration could be incorrect or client is offline
            raise CommunicationError(
                f"Failed to send a message to {recipient} (after {retryer.statistics.get('attempt_number', 0)} attempts)."
            ) from e

    async def _try_send(self, connection: HttpConnection, packet: bytes) -> None:
        """
        Implement the actual sending of a packet by making a HTTP POST request.

        :param client: The connection to send the packet through.
        :param packet: The bytes to send.
        :raise CommunicationError: if the response was not `200 OK`.
        """
        proto = "https" if self.use_ssl else "http"
        url = f"{proto}://{connection.addr}:{connection.port}"
        kwargs: dict[str, Any] = {"data": packet, "timeout": self.conn_timeout}
        kwargs = kwargs | ({"ssl": self.ssl_client_context} if self.use_ssl else {})
        resp = await connection.session.post(url, **kwargs)

        if resp.status != web.HTTPOk.status_code:
            raise CommunicationError(
                f"Received status code {resp.status} from client ({connection.network_id}). Reason: {resp.reason}"
            )

    @staticmethod
    async def _get_handler(_request: web.Request) -> web.Response:
        """
        The main handler for all incoming GET requests.

        Simply returns 200 OK to indicate that the server is up and running.

        :param _request: the incoming request
        :return: a response
        """
        return web.Response(text="Connection working (GET)")

    async def _post_handler(self, request: web.Request) -> web.Response:
        """
        The main handler for all incoming POST requests.

        The handler tries to associate the traffic with the matching
        `HttpConnection` and sends the received packet to the
        `receive_handler`.

        :param request: the incoming request
        :raise Exception: a re-raise of the exception that occured (for logging purposes)
        :raise web.HTTPBadRequest: raised when server_port cookie is not set
        :return: a response
        """
        # Attempt to read the incoming request.
        try:
            response = await request.read()
            assert request.content_length is not None
        except Exception as exception:
            logger.exception("Something went wrong in loading received response.")
            raise exception

        # Determine the port used by the sender
        server_port = request.cookies.get("server_port", None)

        logger.info(f"Received message from {request.remote}:{server_port}")
        logger.debug(f"Message contains {response[0:min(100,len(response))]!r}...")

        if server_port is None:
            logger.error("HTTP POST does not contain the server_port cookie.")
            raise web.HTTPBadRequest()

        if self.use_ssl and not request.secure:
            raise CommunicationError(
                "SSL is enabled but received non-secure HTTP POST request."
            )

        # If it uses SSL, we use the certificate to determine the sender id.
        # Otherwise, we use the address and port as sender id.
        if self.use_ssl:
            transport = cast(Transport, request.transport)
            client_cert = transport.get_extra_info("peercert")
            issuer_common_name = client_cert["issuer"][0][0][1]
            cert_serial_number = int(client_cert["serialNumber"], 16)
            sender_id = f"{issuer_common_name}:{cert_serial_number}"
        else:
            sender_id = f"{request.remote}:{server_port}"

        # Call the receive_handler on the Pool for further processing of the incoming message.
        try:
            sender_name = self._get_connection_name_by_network_id(sender_id)
            await self.receive_handler(sender_name, response)  # pylint: disable=E1102
        except KeyError:
            logger.error(f"Received message from unknown sender: {sender_id}")
            raise web.HTTPUnauthorized(reason="Server did not recognize sender.")
        except Exception as e:
            raise web.HTTPBadRequest(
                reason=f"Failed processing received message: '{e}'"
            )
        return web.Response(text="Message received")

    @override
    async def _shutdown(self) -> None:
        """
        Shutdown the `HttpCommunicator` by closing all pending connections and
        shutting down the HTTP server.
        """
        # Close all connections
        for connection in self._connections.values():
            await connection.close()

        # Stop the server.
        if self._runner:
            logger.debug("HTTPServer: Shutting down server")
            await self._runner.cleanup()

    def _get_connection_name_by_network_id(self, network_id: str) -> str:
        """
        Return the name identifying the connection associated to the given
        network identifier.

        :param: A network identifier.
        :return: The connection name.
        """
        for name, client in self._connections.items():
            if _is_same_network_id(client.network_id, network_id):
                return name
        raise KeyError(f"No client found with network_id `{network_id}`.")

    def __str__(self) -> str:
        """
        String representation of Self.
        """
        return f"HttpCommunicator(addr={self.addr}, port={self.port})"


def _is_same_network_id(
    network_id1: str,
    network_id2: str,
) -> bool:
    """
    Check if two network identifiers are the same.

    :param network_id1: The first network identifier.
    :param network_id2: The second network identifier.
    :return: True if the two identifiers are the same, False otherwise.
    """
    LOCALHOST_IDS = ["localhost", "127.0.0.1", "::1"]
    for localhost_id in LOCALHOST_IDS:
        if network_id1.startswith(localhost_id):
            network_id1 = network_id1.replace(localhost_id, "localhost", 1)
        if network_id2.startswith(localhost_id):
            network_id2 = network_id2.replace(localhost_id, "localhost", 1)
    return network_id1 == network_id2
