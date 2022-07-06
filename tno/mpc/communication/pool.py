"""
This module contains the Pool class used to communicate between parties
"""

from __future__ import annotations

import asyncio
import functools
import logging
import socket
import ssl
from asyncio import Future
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union, cast

from aiohttp import ClientTimeout

from .functions import init
from .httphandlers import HTTPClient, HTTPServer
from .serialization import DEFAULT_PACK_OPTION, Serialization

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
        timeout: ClientTimeout = ClientTimeout(total=300),
        max_retries: int = -1,
    ):
        """
        Initalises a pool

        :param key: path to the key to use in the ssl context
        :param cert: path to the certificate to use in the ssl context
        :param ca_cert: path to the certificate authority (CA) certificate to use in the ssl context
        :param timeout: default timeout for client connections
        :param max_retries: default maximum number of retries for sending a message (-1 for unbounded retries)
        """
        self.key = key
        self.cert = cert
        self.ca_cert = ca_cert
        self.default_timeout = timeout
        self.default_max_retries = max_retries

        self.loop = asyncio.get_event_loop()
        self.http_server: Optional[HTTPServer] = None
        self.pool_handlers: Dict[str, HTTPClient] = {}
        self.handlers_lookup: Dict[str, HTTPClient] = {}

    def add_http_server(
        self,
        port: Optional[int] = None,
        addr: str = "0.0.0.0",
        external_port: Optional[int] = None,
    ) -> None:
        """
        Add an HTTP Server to the pool.

        :param addr: (ip) address of the server
        :param port: the port to bind to. In case of port forwarding, this is the internal port
        :param external_port: optional external port that can be set in case of port forwarding.
            In that case, the external port only serves as identification of this sender to other parties.
            It should be equal to the port that is visible to other parties
            (i.e. the port that other parties will send their messages to).
        """
        ssl_ctx = self.create_ssl_context(
            self.key, self.cert, self.ca_cert, server=True
        )
        port = self.get_port(ssl_ctx) if port is None else port

        self.http_server = HTTPServer(
            self, addr=addr, port=port, external_port=external_port, ssl_ctx=ssl_ctx
        )

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

    def _preprocess_broadcast(
        self,
        handler_names: Optional[List[str]] = None,
        timeout: Optional[ClientTimeout] = None,
        max_retries: Optional[int] = None,
    ) -> Tuple[ClientTimeout, int, List[HTTPClient], bool, int]:
        """
        Preprocessing for the broadcast method

        :param handler_names: the names of the pool handlers to send a message to (if None, will broadcast to all known
            handlers)
        :param timeout: timeout for the connection, if not set use default_timeout
        :param max_retries: maximum number of retries for sending the message, if not set use default_max_retries
            (-1 for unbounded retries)
        :return: Tuple consisting of parsed value for 1) client timeout, 2) max retries, 3) HTTPClient handlers,
            4) boolean use_pickle, 5) ormsgpack option.
        """
        if timeout is None:
            timeout = self.default_timeout
        if max_retries is None:
            max_retries = self.default_max_retries
        if handler_names is None:
            handlers = list(self.pool_handlers.values())
        else:
            handlers = [
                self.pool_handlers[handler_name] for handler_name in handler_names
            ]

        use_pickle = all(map(lambda h: h.use_pickle, handlers))
        option = functools.reduce(
            lambda x, y: x & y,
            map(
                lambda h: DEFAULT_PACK_OPTION if h.option is None else h.option,
                handlers,
            ),
        )

        # we need to update the msg_send_counter
        for handler in handlers:
            handler.msg_send_counter += 1

        return timeout, max_retries, handlers, use_pickle, option

    def async_broadcast(
        self,
        message: Any,
        msg_id: str,
        handler_names: Optional[List[str]] = None,
        timeout: Optional[ClientTimeout] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        """
        Send a message to multiple other parties asynchronously.
        Serializes the message and schedules the sending of the message and returns immediately after that.
        There is no assurance of feedback about the message being delivered.

        :param message: the message to send
        :param msg_id: a string identifying the message to send
        :param handler_names: the names of the pool handlers to send a message to (if None, will broadcast to all known
            handlers)
        :param timeout: timeout for the connection, if not set use default_timeout
        :param max_retries: maximum number of retries for sending the message, if not set use default_max_retries
            (-1 for unbounded retries)
        """
        timeout, max_retries, handlers, use_pickle, option = self._preprocess_broadcast(
            handler_names, timeout, max_retries
        )

        data = Serialization.pack(
            obj=message,
            msg_id=msg_id,
            use_pickle=use_pickle,
            option=option,
            destination=handlers,
        )
        for handler in handlers:
            self.loop.create_task(
                handler._send(data, timeout=timeout, num_retries=max_retries)
            )

    async def broadcast(
        self,
        message: Any,
        msg_id: str,
        handler_names: Optional[List[str]] = None,
        timeout: Optional[ClientTimeout] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        """
        Send a message to multiple other parties synchronously

        :param message: the message to send
        :param msg_id: a string identifying the message to send
        :param handler_names: the names of the pool handlers to send a message to (if None, will broadcast to all known
            handlers)
        :param timeout: timeout for the connection, if not set use default_timeout
        :param max_retries: maximum number of retries for sending the message, if not set use default_max_retries
            (-1 for unbounded retries)
        """
        timeout, max_retries, handlers, use_pickle, option = self._preprocess_broadcast(
            handler_names, timeout, max_retries
        )

        data = await self.loop.run_in_executor(
            None,
            functools.partial(
                Serialization.pack,
                obj=message,
                msg_id=msg_id,
                use_pickle=use_pickle,
                option=option,
                destination=handlers,
            ),
        )
        await asyncio.gather(
            *(
                self.loop.create_task(
                    handler._send(data, timeout=timeout, num_retries=max_retries)
                )
                for handler in handlers
            )
        )

    def asend(
        self,
        handler_name: str,
        message: Any,
        msg_id: Optional[str] = None,
        timeout: Optional[ClientTimeout] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        """
        Send a message to peer asynchronously.
        Schedules the sending of the message and returns immediately.
        There is no assurance of feedback about the message being delivered.

        :param handler_name: the name of the pool handler to send a message to
        :param message: the message to send
        :param msg_id: an optional string identifying the message to send
        :param timeout: timeout for the connection, if not set use default_timeout
        :param max_retries: maximum number of retries for sending the message, if not set use default_max_retries
            (-1 for unbounded retries)
        """
        if timeout is None:
            timeout = self.default_timeout
        if max_retries is None:
            max_retries = self.default_max_retries
        self.loop.create_task(
            self._get_handler(handler_name).send(
                message, msg_id, timeout=timeout, max_retries=max_retries
            )
        )

    async def send(
        self,
        handler_name: str,
        message: Any,
        msg_id: Optional[str] = None,
        timeout: Optional[ClientTimeout] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        """
        Send a message to peer synchronously.

        :param handler_name: the name of the pool handler to send a message to
        :param message: the message to send
        :param msg_id: an optional string identifying the message to send
        :param timeout: timeout for the connection, if not set use default_timeout
        :param max_retries: maximum number of retries for sending the message, if not set use default_max_retries
            (-1 for unbounded retries)
        """
        if timeout is None:
            timeout = self.default_timeout
        if max_retries is None:
            max_retries = self.default_max_retries
        await self._get_handler(handler_name).send(
            message, msg_id, timeout=timeout, max_retries=max_retries
        )

    def arecv(self, handler_name: str, msg_id: Optional[str] = None) -> Future[Any]:
        """
        Receive a message synchronously from a peer.

        :param handler_name: the name of the pool handler to receive a message from
        :param msg_id: an optional string identifying the message to collect
        :return: the message from peer or a Future.
        """
        return self._get_handler(handler_name).recv(msg_id)

    def arecv_all(
        self,
        handler_names: Optional[Iterable[str]] = None,
        msg_id: Optional[str] = None,
    ) -> Tuple[Tuple[str, Future[Any]], ...]:
        """
        Method that receives one message for each party in a synchronous fashion.

        :param handler_names: List of pool handler names to receive a message from. If None, will receive one message
             from all parties.
        :param msg_id: an optional string identifying the message to collect
        :return: Tuple of tuples containing first the party name and second the corresponding message or future.
        """
        if handler_names is None:
            handler_names = self.pool_handlers.keys()

        return tuple(
            (handler, self._get_handler(handler).recv(msg_id))
            for handler in handler_names
        )

    async def recv_all(
        self,
        handler_names: Optional[Iterable[str]] = None,
        msg_id: Optional[str] = None,
    ) -> Tuple[Tuple[str, Any]]:
        """
        Method that receives one message for each party in an asynchronous fashion.

        :param handler_names: List of pool handler names to receive a message from. If None, will receive one message
             from all parties.
        :param msg_id: an optional string identifying the message to collect
        :return: Tuple of tuples containing first the party name and second the corresponding message.
        """
        if handler_names is None:
            handler_names = self.pool_handlers.keys()

        async def result_tuple(handler: str) -> Tuple[str, Any]:
            """
            Receive a message from the given handler, using the outer scope msg_id.

            :param handler: Pool handler name to receive a message from.
            :return: Tuple containing first the party name and second the received message.
            """
            return handler, await self.recv(handler, msg_id)

        return await asyncio.gather(*(result_tuple(handler_name) for handler_name in handler_names))  # type: ignore[no-any-return]

    async def recv(self, handler_name: str, msg_id: Optional[str] = None) -> Any:
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
        return result

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all connections/listeners in the pool.
        """
        total_bytes_sent = 0
        msg_send_counter = 0
        total_bytes_recv = 0
        msg_recv_counter = 0
        if self.http_server is not None:
            await self.http_server.shutdown()
            msg_recv_counter = self.http_server.msg_recv_counter
            total_bytes_recv = self.http_server.total_bytes_recv
        for handler in self.pool_handlers.values():
            await handler.shutdown()
            total_bytes_sent += handler.total_bytes_sent
            msg_send_counter += handler.msg_send_counter
        self.pool_handlers = {}
        self.handlers_lookup = {}
        logger.info(
            f"Pool shutdown.\nTotal bytes sent: {total_bytes_sent}\nTotal messages sent: {msg_send_counter}\nTotal bytes received: {total_bytes_recv}\nTotal messages received: {msg_recv_counter}"
        )

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
