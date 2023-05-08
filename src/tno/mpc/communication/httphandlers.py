"""
This module contains classes for the HTTP server and the HTTP client
"""

from __future__ import annotations

import asyncio
import functools
import logging
import ssl
import sys
from asyncio import Future, Transport
from typing import Any, Awaitable, Callable, cast, overload

from aiohttp import ClientSession, ClientTimeout, web

from .functions import init
from .serialization import DEFAULT_PACK_OPTION, Serialization

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


logger = init(__name__, logger_level=logging.INFO)


class AbstractPool(Protocol):
    """
    Protocol that mimics tno.mpc.communication.Pool.

    This protocol contains the minimal Pool interface needed by HTTPClient and
    HTTPServer. The next major release likely removes the pool parameter entirely in
    favor of passing the few required attributes directly.
    """

    http_server: None | HTTPServer
    loop: asyncio.AbstractEventLoop
    handlers_lookup: dict[str, HTTPClient]


class HTTPClient:
    """
    Class that serves as an HTTP Client
    """

    def __init__(
        self,
        pool: AbstractPool,
        addr: str,
        port: int,
        ssl_ctx: ssl.SSLContext | None,
        option: int | None = DEFAULT_PACK_OPTION,
        use_pickle: bool = False,
        msg_prefix: str | None = None,
    ):
        """
        Initializes an HTTP client instance

        :param pool: the communication pool to use
        :param addr: the address of the client
        :param port: the port of the client
        :param ssl_ctx: an optional ssl context
        :param option: ormsgpack options can be specified through this parameter
        :param use_pickle: set to True to enable serialization fallback to pickle
        :param msg_prefix: prefix for all sent and received message (e.g. a session id)
        :raise AttributeError: raised when the provided pool has no assigned http server
        """
        self.pool = pool
        self.addr = addr
        self.port = port
        self.ssl_ctx = ssl_ctx
        self.option = option
        self.use_pickle = use_pickle
        self.msg_prefix = msg_prefix
        if self.pool.http_server is None:
            raise AttributeError("No HTTP Server initialized (yet).")
        self.session: ClientSession
        cookies = {"server_port": str(self.pool.http_server.external_port)}
        if self.pool.loop.is_running():
            self.pool.loop.create_task(self._create_client_session(cookies))
        else:
            self.pool.loop.run_until_complete(self._create_client_session(cookies))
        self.msg_send_counter = 0
        self.total_bytes_sent = 0
        self.msg_recv_counter = 0
        self.buffer: dict[str | int, Future[dict[str, Any]]] = {}

    def __eq__(self, other: object) -> bool:
        """
        Equality check for HTTP Clients

        :param other: another HTTP Client
        :return: whether they have the same address and port
        """
        if not isinstance(other, HTTPClient):
            return False
        return self.addr == other.addr and self.port == other.port

    @staticmethod
    @overload
    def _prefix_msg_id(msg_id: str, msg_prefix: str | None) -> str:
        ...

    @staticmethod
    @overload
    def _prefix_msg_id(msg_id: int, msg_prefix: str) -> str:
        ...

    @staticmethod
    @overload
    def _prefix_msg_id(msg_id: int, msg_prefix: None) -> int:
        ...

    @staticmethod
    def _prefix_msg_id(msg_id: str | int, msg_prefix: str | None) -> str | int:
        """
        Prepend msg_id with the set msg_prefix

        :param msg_id: the msg_id to prefix
        :param msg_prefix: message prefix to use
        :return: prefixed msg_id
        """
        if msg_prefix is not None:
            return msg_prefix + str(msg_id)
        return msg_id

    async def shutdown(self) -> None:
        """
        Shutdown HTTP Client. Closes open HTTP session.
        """
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info(
                f"Client {self.addr}:{self.port} shutdown\nTotal bytes sent: {self.total_bytes_sent}\nTotal messages sent: {self.msg_send_counter}"
            )

    async def send(
        self,
        message: Any,
        msg_id: str | int | None = None,
        retry_delay: int = 1,
        timeout: ClientTimeout = ClientTimeout(total=300),
        max_retries: int = -1,
    ) -> None:
        """
        Sends a POST JSON request to containing the message to this client.
        If sending of message fails and retry_delay > 0 then retry after retry_delay seconds

        :param message: the message to send
        :param msg_id: an optional identifier of the message to send
        :param retry_delay: number of seconds to wait before retrying after failure
        :param timeout: timeout for the connection
        :param max_retries: maximum number of retries for sending the message (-1 for unbounded retries)
        """
        if msg_id is None:
            msg_id = self.msg_send_counter
        if self.msg_prefix is not None:
            msg_id = HTTPClient._prefix_msg_id(msg_id, self.msg_prefix)
        self.msg_send_counter += 1

        data = await self.pool.loop.run_in_executor(
            None,
            functools.partial(
                Serialization.pack,
                obj=message,
                msg_id=msg_id,
                use_pickle=self.use_pickle,
                option=self.option,
                destination=self,
            ),
        )
        await self._send(data, retry_delay, timeout=timeout, num_retries=max_retries)

    async def _send(
        self,
        data: bytes,
        retry_delay: int = 1,
        timeout: ClientTimeout = ClientTimeout(total=300),
        num_retries: int = -1,
    ) -> None:
        """
        Sends a POST request to containing this data to this client.
        If sending of message fails and retry_delay > 0 then retry after retry_delay seconds

        :param data: the data to send
        :param retry_delay: number of seconds to wait before retrying after failure
        :param timeout: timeout for the connection
        :param num_retries: number of retries that are allowed for sending the message (-1 for unbounded retries)
        """
        try:
            async with self.session.post(
                f"http{'s' if self.ssl_ctx else ''}://{self.addr}:{self.port}",
                data=data,
                ssl=self.ssl_ctx,
                timeout=timeout,
            ) as resp:
                logger.debug(
                    f"Sending data... of {len(data)} bytes to {self.addr}:{self.port}"
                )
                assert resp.status == 200, "Did not receive status OK (200)"

                response_message = await resp.text()

                self.total_bytes_sent += len(data)

                logger.debug(f"Response: {response_message}")
        except Exception:
            logger.exception("Message not received.")
            if retry_delay and num_retries != 0:
                logger.debug(
                    f"Connection failed. Retrying ({num_retries} attempts remaining), url: {self.addr}:{self.port}, data:"
                    f" {data[0:min(100,len(data))]!r}..."
                )
                await asyncio.sleep(retry_delay)
                await asyncio.create_task(
                    self._send(
                        data,
                        retry_delay,
                        timeout=timeout,
                        num_retries=max(num_retries - 1, -1),
                    )
                )
            else:
                logger.debug("Connection failed. Will not retry.")

    def recv(self, msg_id: str | int | None = None) -> Future[dict[str, Any]]:
        """
        Request a message from this client

        :param msg_id: an optional identifier of the message to receive
        :return: the received message
        """
        if msg_id is None:
            msg_id = self.msg_recv_counter
        msg_id = HTTPClient._prefix_msg_id(msg_id, self.msg_prefix)
        self.msg_recv_counter += 1

        data = self.buffer.pop(msg_id, None)
        if data is None:
            fut: Future[dict[str, Any]]
            fut = self.buffer[msg_id] = Future()
            return fut
        return data

    async def _create_client_session(self, cookies: dict[str, str]) -> None:
        """
        Create an aiohttp ClientSession for use with this HTTPClient. This method should only be
        called once during construction.

        :param cookies: Cookies for this ClientSession
        """
        self.session = ClientSession(
            cookies=cookies,
        )


class HTTPServer:
    """
    Class for serving an HTTP server
    """

    def __init__(
        self,
        pool: AbstractPool,
        port: int,
        external_port: int | None = None,
        addr: str = "0.0.0.0",
        ssl_ctx: ssl.SSLContext | None = None,
        get_handler: None
        | (Callable[[web.Request], Awaitable[web.StreamResponse]]) = None,
        post_handler: None
        | (Callable[[web.Request], Awaitable[web.StreamResponse]]) = None,
        option: int | None = None,
        use_pickle: bool = False,
    ):
        """
        Initalizes an HTTP server instance

        :param pool: the communication pool to use
        :param port: the port to bind to. In case of port forwarding, this is the internal port
        :param external_port: optional external port that can be set in case of port forwarding.
            In that case, the external port only serves as identification of this sender to other parties.
            It should be equal to the port that is visible to other parties
            (i.e. the port that other parties will send their messages to).
        :param addr: the address to bind to
        :param ssl_ctx: an optional ssl context
        :param get_handler: an optional GET handler to use
        :param post_handler: an optional POST handler to use
        :param option: ormsgpack options can be specified through this parameter
            use_pickle: bool = False,
        """
        self.pool = pool
        self.addr = addr
        self.port = port
        if external_port is None:
            self.external_port = port
        else:
            self.external_port = external_port
        self.ssl_ctx = ssl_ctx
        self.option = option
        self.use_pickle = use_pickle
        self.loop = pool.loop
        self.site: web.TCPSite | None = None
        self.msg_recv_counter = 0
        self.total_bytes_recv = 0

        self.server_task = self.loop.create_task(
            self.run_server(get_handler, post_handler)
        )

    async def shutdown(self) -> None:
        """
        Shutdown HTTP Server.
        """
        if self.site:
            logger.debug("HTTPServer: Shutting down site")
            await self.site.stop()
        if self.server_task and not self.server_task.cancelled():
            logger.info("HTTPServer: Shutting down server task")
            self.server_task.cancel()
        logger.info(
            f"Server {self.addr}:{self.port} shutdown\nTotal bytes received: {self.total_bytes_recv}\nTotal messages received: {self.msg_recv_counter}"
        )

    async def _post_handler(self, request: web.Request) -> web.Response:
        """
        Handles an incoming HTTP POST request and writes every JSON POST request to socket.

        :param request: the incoming request
        :raise Exception: a re-raise of the exception that occured (for logging purposes)
        :raise web.HTTPUnauthorized: raised when post_handler is not set
        :raise web.HTTPBadRequest: raised when server_port cookie is not set
        :return: a response
        """
        try:
            response = await request.read()
            assert request.content_length is not None
            response_size: int = request.content_length
        except Exception as exception:
            logger.exception("Something went wrong in loading received response.")
            raise exception

        server_port = request.cookies.get("server_port", None)

        logger.info(f"Received message from {request.remote}:{server_port}")
        logger.debug(f"Message contains {response[0:min(100,len(response))]!r}...")

        if server_port is None:
            logger.error("HTTP POST does not contain the server_port cookie.")
            raise web.HTTPBadRequest()

        handler_id_from_cert = ""
        handler_not_found_msg = "Handler not found for "
        if request.secure:
            transport = cast(Transport, request.transport)
            client_cert = transport.get_extra_info("peercert")
            issuer_common_name = client_cert["issuer"][0][0][1]
            cert_serial_number = int(client_cert["serialNumber"], 16)
            handler_id_from_cert = f"{issuer_common_name}:{cert_serial_number}"
            handler_not_found_msg += f"{handler_id_from_cert} or "
        handler_id_from_address = f"{request.remote}:{server_port}"
        handler_not_found_msg += f"{handler_id_from_address}."

        if handler_id_from_cert in self.pool.handlers_lookup:
            handler = self.pool.handlers_lookup.get(handler_id_from_cert, None)
        elif handler_id_from_address in self.pool.handlers_lookup:
            handler = self.pool.handlers_lookup.get(handler_id_from_address, None)
        else:
            logger.error(handler_not_found_msg)
            raise web.HTTPUnauthorized()
        handler = cast(HTTPClient, handler)

        msg_id, message = await self.loop.run_in_executor(
            None,
            functools.partial(
                Serialization.unpack,
                obj=response,
                use_pickle=self.use_pickle,
                option=self.option,
                origin=handler,
            ),
        )
        if msg_id in handler.buffer:
            try:
                handler.buffer.pop(msg_id).set_result(message)
            except AttributeError:
                logger.exception(
                    f"Message id: {msg_id} is not a future. "
                    f"This could mean that the sending party "
                    f"is re-using this message ID, "
                    f"or that you already received this message."
                )
        else:
            handler.buffer[msg_id] = message

        self.msg_recv_counter += 1
        self.total_bytes_recv += response_size
        return web.Response(text="Message received")

    @staticmethod
    async def _get_handler(_request: web.Request) -> web.Response:
        """
        Handles an incoming HTTP GET request.

        :param _request: the incoming request
        :return: a response
        """
        return web.Response(text="Connection working (GET)")

    async def run_server(
        self,
        get_handler: None
        | (Callable[[web.Request], Awaitable[web.StreamResponse]]) = None,
        post_handler: None
        | (Callable[[web.Request], Awaitable[web.StreamResponse]]) = None,
    ) -> None:
        """
        Initializes the HTTP server.

        :param get_handler: a custom GET handler to handle GET requests
        :param post_handler: a custom POST handler to handle POST requests
        """
        app = web.Application(client_max_size=0)
        app.router.add_post(
            "/{tail:.*}", post_handler if post_handler else self._post_handler
        )
        app.router.add_get(
            "/{tail:.*}", get_handler if get_handler else self._get_handler
        )
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(
            runner, host=self.addr, port=self.port, ssl_context=self.ssl_ctx
        )
        await self.site.start()

        logger.info(
            f"Serving on {self.addr}:{str(self.port)}{' with TLS' if self.ssl_ctx else ''}"
        )
