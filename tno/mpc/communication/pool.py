"""
This module contains the Pool class used to communicate between parties
"""

import asyncio
import logging
import socket
import ssl
import threading
from asyncio import Future
from typing import cast, Any, Dict, Optional

from .functions import init
from .httphandlers import HTTPClient, HTTPServer

logger = init(__name__, logger_level=logging.DEBUG)


class Pool:
    """
    Facilitates a communication pool that enables communication between us (server) and others (clients).
    """

    def __init__(
        self,
        key: Optional[str] = None,
        cert: Optional[str] = None,
        ca_cert: Optional[str] = None,
    ):
        """
        Initalises a pool

        :param key: path to the key to use in the ssl context
        :param cert: path to the certificate to use in the ssl context
        :param ca_cert: path to the certificate authority (CA) certificate to use in the ssl context
        """
        self.key = key
        self.cert = cert
        self.ca_cert = ca_cert

        self.loop = asyncio.get_event_loop()
        self.http_server: Optional[HTTPServer] = None
        self.pool_handlers: Dict[str, HTTPClient] = {}
        self.handlers_lookup: Dict[str, HTTPClient] = {}
        self.msg_counter = 0
        self.lock = threading.Lock()

    def add_http_server(
        self, port: Optional[int] = None, addr: str = "0.0.0.0"
    ) -> None:
        """
        Add an HTTP Server to the pool.

        :param addr: (ip) address of the server
        :param port: port of the server
        """
        ssl_ctx = self.create_ssl_context(
            self.key, self.cert, self.ca_cert, server=True
        )
        port = self.get_port(ssl_ctx) if port is None else port

        self.http_server = HTTPServer(self, addr=addr, port=port, ssl_ctx=ssl_ctx)

    def add_http_client(self, name: str, addr: str, port: Optional[int] = None) -> None:
        """
        Add an HTTP Client to the pool. addr can be either an IP address or a
        hostname.

        :param name: name of the client
        :param addr: (ip) address of the client
        :param port: port of the client
        """
        ssl_ctx = self.create_ssl_context(self.key, self.cert, self.ca_cert)
        port = self.get_port(ssl_ctx) if port is None else port
        client = HTTPClient(self, addr, port, ssl_ctx)
        self.pool_handlers[name] = client
        self.handlers_lookup[f"{socket.gethostbyname(addr)}:{port}"] = client

    @staticmethod
    def create_ssl_context(
        key: Optional[str],
        cert: Optional[str],
        ca_cert: Optional[str] = None,
        server: bool = False,
    ) -> Optional[ssl.SSLContext]:
        """
        Create an SSL context.

        :param key: path to the key to use in the ssl context
        :param cert: path to the certificate to use in the ssl context
        :param ca_cert: path to the certificate authority (CA) certificate to use in the ssl context
        :param server: boolean stating whether we need a server context or not (client)
        :return: an SSL context or None
        """
        if ca_cert is None:
            return None

        if server:
            purpose = ssl.Purpose.CLIENT_AUTH
        else:
            purpose = ssl.Purpose.SERVER_AUTH

        ctx = ssl.create_default_context(purpose=purpose)
        ctx.load_cert_chain(certfile=cast(str, cert), keyfile=cast(str, key))

        ctx.load_verify_locations(cafile=ca_cert)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_REQUIRED

        return ctx

    @staticmethod
    def get_port(ssl_ctx: Optional[ssl.SSLContext]) -> int:
        """
        Returns a port number based on whether an ssl context is provided, or not.

        :param ssl_ctx: an ssl context
        :return: a port number
        """
        if ssl_ctx is None:
            return 80
        return 443

    def asend(
        self, handler_name: str, message: Any, msg_id: Optional[str] = None
    ) -> None:
        """
        Send a message to peer asynchronously.
        Schedules the sending of the message and returns immediately.
        There is no assurance of feedback about the message being delivered.

        :param handler_name: the name of the pool handler to send a message to
        :param message: the message to send
        :param msg_id: an optional string identifying the message to send
        """
        self.loop.create_task(self._get_handler(handler_name).send(message, msg_id))

    async def send(
        self, handler_name: str, message: Any, msg_id: Optional[str] = None
    ) -> None:
        """
        Send a message to peer synchronously.

        :param handler_name: the name of the pool handler to send a message to
        :param message: the message to send
        :param msg_id: an optional string identifying the message to send
        """
        await self._get_handler(handler_name).send(message, msg_id)

    def arecv(
        self, handler_name: str, msg_id: Optional[str] = None
    ) -> "Future[Dict[str, Any]]":
        """
        Receive a message synchronously from a peer.

        :param handler_name: the name of the pool handler to receive a message from
        :param msg_id: an optional string identifying the message to collect
        :return: the message from peer or a Future.
        """
        return self._get_handler(handler_name).recv(msg_id)

    async def recv(
        self, handler_name: str, msg_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Receive a message asynchronously from a peer. Ensures result.

        :param handler_name: the name of the pool handler to receive a message from
        :param msg_id: an optional string identifying the message to collect
        :return: the message from peer.
        """
        result = self.arecv(handler_name, msg_id)
        if asyncio.isfuture(result):
            await result
            return result.result()
        return cast(Dict[str, Any], result)

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all connections/listeners in the pool.
        """
        if self.http_server:
            await self.http_server.shutdown()
        for handler in self.pool_handlers.values():
            await handler.shutdown()
        self.pool_handlers = {}
        self.handlers_lookup = {}

    def _get_handler(self, handler_name: str) -> HTTPClient:
        """
        Retrieves http client (handler) from the communication pool

        :param handler_name: the name of the pool handler
        :raise AttributeError: raised when the handler is not in the provided pool
        :return: the retrieved HTTPClient
        """
        handler = self.pool_handlers.get(handler_name, None)
        if handler is None:
            raise AttributeError(f'No pool handler named "{handler_name}"')
        return handler
