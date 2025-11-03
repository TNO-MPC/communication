"""
This module contains the Pool class. The Pool is an interface
(and implementation) of a generic "communication pool". A communication pool is
intended to be a small peer-to-peer network that allows for point-to-point and
broadcast communication.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import sys
from asyncio import Future, isfuture
from collections.abc import Iterable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Any

from tno.mpc.communication.buffer import Buffer
from tno.mpc.communication.communicators.communicator import Communicator
from tno.mpc.communication.exceptions import CommunicationError
from tno.mpc.communication.packers.packer import DefaultPacker, Packer

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

logger = logging.getLogger(__name__)


@dataclass
class _Client:
    """
    Class representing a client in a Pool.

    Each `Client` object in a Pool represents a connection and performs some
    message bookkeeping for that connection.
    """

    identifier: str
    """
    The unique identifier of this Client within the Pool.
    """

    total_bytes_sent = 0
    total_bytes_recv = 0
    msg_send_counter = 0
    msg_recv_counter = 0

    def log_network_usage(self) -> None:
        """
        Shutdown Client. Sends statistics to logger.
        """
        logger.info(
            f"Client {self.identifier} shutdown\n"
            f"Total bytes sent: {self.total_bytes_sent}\n"
            f"Total messages sent: {self.msg_send_counter}\n"
            f"Total bytes received: {self.total_bytes_recv}\n"
            f"Total messages received: {self.msg_recv_counter}"
        )

    def reset(self) -> None:
        """
        Reset the client to its initial state.
        """
        self.total_bytes_recv = 0
        self.total_bytes_sent = 0
        self.msg_recv_counter = 0
        self.msg_send_counter = 0


class Pool(AbstractAsyncContextManager["Pool"]):
    """
    Implements a generic communication pool intended for use by other modules
    in the PET Lab.

    The Pool interface exposes a simple communication pool, i.e. a peer-to-peer
    network of nodes (referred to as 'clients') allowing for point-to-point and
    broadcast communication. The Pool interface can be used to easily send and
    receive messages to and from other clients in the pool.

    The Pool provides the following features:
    * addressing: simply address a client by its string identifier
    * message buffering: read/receive the messages in the order of your choosing by receiving messages by id (`pool.recv(sender, msg_id='identifier')`)
    * benchmarking: automatically track your bandwidth usage

    The Pool relies on two other interfaces:
    * The `Communicator` implements the actual "over-the-wire" communication. This allows you to easily change the network protocol/implementation of your Pool (e.g. `Pool(communicator=MockCommunicator)`.
    * The `Packer` is used to serialize your python objects into bytes, allowing one to send arbitrary Python objects.
    """

    def __init__(
        self,
        name: str,
        communicator: Communicator[Any],
        packer: Packer | None = None,
        *,
        timeout: float | None = 3,
    ):
        """
        Initialises a pool.

        :param name: The name under which this Pool is known to other Clients
            in the Pool.
        :param communicator: A communicator object to use for communication.
        :param packer: Optional argument to specify a Packer to serialize the messages.
            Defaults to DefaultPacker if not provided.
        :param timeout: The default maximum time in seconds to wait for
            a message to be received. When the timeout passes, an error is
            thrown. If None, receive calls will wait indefinitely.
        """
        self.name = name

        # Initialize communicator
        self.communicator = communicator
        self.communicator.set_receive_handler(self._receive_handler)

        # Set default packer if none is provided.
        self.packer = packer or DefaultPacker()
        # Initialize dictionary to hold client names and client objects.
        self._clients: dict[str, _Client] = {}
        # Create a buffer to store incoming messages.
        self.buffer: Buffer[Any] = Buffer()

        # Parameters
        self._timeout: float | None = timeout

    async def initialize(self) -> None:
        """
        Initialize and start the communication pool.

        This method calls `Communicator.initialize` which, depending on the
        implementation, performs the necessary steps to setup the connections
        between the clients.
        """
        await self.communicator.initialize()

    def add_client(self, name: str, connection: Any) -> None:
        """
        Add a client to the Pool.

        :param name: The name of the client. You can pick any name as long as
            it is unique within the Pool. The name does not need to have any
            relation to the (network) configuration of the client, and acts purely
            as an identifier to reference the corresponding client.
        :param connection: The connection object to use for communication with
            the client. This object is passed to the communicator to send and
            receive messages.
        :raise KeyError: If no client with the given name is registered.
        """
        if name in self._clients:
            raise KeyError(f"Client with name '{name}' already registered!")

        self._clients[name] = _Client(name)
        self.communicator.add_connection(name, connection)
        self.buffer.add_client(name)

    @property
    def clients(self) -> set[str]:
        """
        Return the names of all clients in the Pool.
        """
        return set(self._clients.keys())

    async def broadcast(
        self,
        message: Any,
        msg_id: str,
        recipient_names: Iterable[str] | None = None,
    ) -> None:
        """
        Broadcast a message to all clients in the Pool.

        Unless specified otherwise through `handler_names`, the message is
        broadcast to all clients in the Pool.

        :param message: The message to send.
        :param msg_id: String identifying the message to send.
        :param recipient_names: The names of the clients to send the message to. If None, will broadcast to all known clients.
        :raise ValueError: Raised if not all clients in the pool have been configured with the same message prefix.
        """
        # Convert recipient names to recipient objects
        recipient_names = list(recipient_names or self.clients)

        msg_ids: list[str] = []
        send_tasks = []
        for recipient in recipient_names:
            # Determine the message identifier for the recipient.
            msg_ids.append(msg_id or str(self._clients[recipient].msg_send_counter))

            # Update the message counter for the recipient.
            self._clients[recipient].msg_send_counter += 1

        # Synchronously pack the message.
        datas = await asyncio.get_running_loop().run_in_executor(
            None,
            functools.partial(
                self.packer.pack_multiple,
                content=message,
                msg_ids=msg_ids,
            ),
        )

        # Synchronously send the message to the recipient.
        for recipient, data in zip(recipient_names, datas):
            task = asyncio.create_task(self.communicator.send(recipient, data))
            send_tasks.append(task)

        # Wait for all messages to be sent.
        await asyncio.gather(*(send_tasks))

    async def send(
        self,
        recipient_name: str,
        message: Any,
        msg_id: str | None = None,
    ) -> None:
        """
        Send a message to a single client in the Pool.

        The `recipient_name` is the destination of the message and must match
        the name of one of the `Client`s in the `Pool`.

        :param recipient_name: The name of the pool handler to send a message to.
        :param message: The message to send.
        :param msg_id: An optional string identifying the message to send.
        """
        # Preprocessing of the parameters
        recipient = self._clients[recipient_name]
        msg_id = msg_id or str(recipient.msg_send_counter)
        recipient.msg_send_counter += 1

        # Synchronously convert the message to bytes
        data = await asyncio.get_running_loop().run_in_executor(
            None,
            functools.partial(
                self.packer.pack,
                content=message,
                msg_id=msg_id,
            ),
        )
        # Send the message
        await self.communicator.send(recipient_name, data)
        # Update counters on bytes sent
        recipient.total_bytes_sent += len(data)

    async def recv(
        self,
        sender_name: str,
        msg_id: str | None = None,
        timeout: float | None = None,
    ) -> Any:
        """
        Receive a message from a client in the pool.

        This method returns a single message, the message specified by the
        given `msg_id`.

        If the specfied message has arrived, the message will be returned. If
        not, a `Future` will be returned that is resolved once the message
        arrives. This method is non-blocking.

        Note: One should not reuse `msg_id`s, as this could result in undefined
        behaviour. If you really want to reuse `msg_id`s, _you_ have to ensure
        that either 1) the order in which the messages are received does not
        matter, or 2) make sure that the messages with overlapping `msg_id` are
        only sent once the previous must have been received.

        :param sender_name: The name of the client to receive a message from.
        :param msg_id: An optional string identifying the message to collect.
        :param timeout: Maximum time in seconds to wait for the message to be
            received. If None, will use the timeout of the Pool. Note that the
            default value of the Pool timeout is None, meaning the message is
            awaited indefinitely.
        :raise CommunicationError: If no message was received before timeout.
        :return: A received message or a future for the message.
        """
        sender = self._clients[sender_name]

        # Determine message identifier for the message.
        msg_id = msg_id or str(sender.msg_recv_counter)
        sender.msg_recv_counter += 1

        # If a message with that id is available in the buffer, return it.
        if self.buffer.has_message(sender_name, msg_id):
            return self.buffer.pop(sender_name, msg_id)

        # Otherwise, push a future to the buffer and return it.
        # If a message arrives with this id in the future, pool._receive_handler will set
        # the message as the result of the future.
        future: Future[dict[str, Any]] = Future()
        self.buffer.push(sender_name, msg_id, future)
        try:
            await asyncio.wait_for(future, timeout=timeout or self._timeout)
        except (TimeoutError, asyncio.TimeoutError) as e:
            raise CommunicationError(
                f"Did not receive the requested messages within the specified "
                f"timeout of {timeout or self._timeout} seconds. This likely "
                f"indicates a problem in your implementation (you are trying to "
                f"receive a message that is never sent). If you suspect this is "
                f"a networking problem, you can try to increase the timeout "
                f"either via `Pool.recv(timeout=...)` or by setting the global "
                f"timeout in `Pool(timeout=...)`."
            ) from None
        return future.result()

    async def recv_all(
        self,
        sender_names: Iterable[str] | None = None,
        msg_id: str | None = None,
        timeout: float | None = None,
    ) -> list[tuple[str, Any]]:
        """
        Receive one message for each client in the `Pool`
        (or a subset if `sender_names` is provided).

        See also :meth:`Pool.recv`.

        :param sender_names: List of client names to receive a message from. If None, it will
            receive one message from all parties.
        :param msg_id: An optional string identifying the message to collect.
        :param timeout: Maximum time in seconds to wait for the message to be
            received. If None, will use the timeout of the Pool. Note that the
            default value of the Pool timeout is None, meaning the message is
            awaited indefinitely.
        :raise TimeoutError: Message was not received before timeout.
        :return: Sequence of tuples containing first the client name and second
            the corresponding message or future.
        """
        sender_names = sender_names or self.clients

        async def result_tuple(sender_name: str) -> tuple[str, Any]:
            """
            Receive a message from the given sender, using the outer scope msg_id.

            :param sender_name: Sender name to receive a message from.
            :return: Tuple containing first the party name and second the received message.
            """
            return sender_name, await self.recv(
                sender_name, msg_id, timeout=timeout or self._timeout
            )

        return await asyncio.gather(
            *(result_tuple(sender_name) for sender_name in sender_names)
        )

    async def _receive_handler(self, sender_name: str, packet: bytes) -> None:
        """
        Handles the processing of receiving a packet from a given
        client. Should be called by the Communicator upon receiving a packet.

        Note: To keep a consistent buffer state, one must ensure that each
        incoming message is retrieved (through `Pool.recv` and friends) exactly
        once. Messages in the buffer that are never retrieved will remain
        dangling. Incoming messages with the same message id will overwrite
        each other, resulting in undefined behavior.

        :param sender_name: The name of the sender of the message.
        :param packet: The incoming message.
        :raise KeyError: If no Client is registered to the Pool with the given
            sender_id.
        """
        # Get the local client name and object based on sender id
        if not (sender := self._clients.get(sender_name, None)):
            raise KeyError(
                f"No client with name `{sender_name}` is registered to this Pool."
            )

        # Unpack the message into message id and content
        msg_id, message = await asyncio.get_running_loop().run_in_executor(
            None,
            functools.partial(
                self.packer.unpack,
                packet=packet,
            ),
        )

        # If there is a future for this sender and message id on the buffer, set the result in the future.
        # Otherwise, push the message onto the buffer.
        if self.buffer.has_message(sender_name, msg_id):
            try:
                self.buffer.pop(sender_name, msg_id).set_result(message)
            except AttributeError:
                logger.exception(
                    f"Message id: {msg_id} is not a future. "
                    f"This could mean that the sending party "
                    f"is re-using this message ID, "
                    f"or that you already received this message."
                )
        else:
            self.buffer.push(sender_name, msg_id, message)

        # Update number of bytes received.
        sender.total_bytes_recv += len(packet)

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all connections/listeners in the pool.
        """
        # Cancel pending futures (unreceived messages)
        count = 0
        for client in self._clients.values():
            buffer = self.buffer.get_client(client.identifier)
            for item in buffer.values():
                if isfuture(item):
                    item.cancel()
                    count += 1
        if count > 0:
            logger.warning(
                f"There are {count} messages being awaited that have not yet been received."
            )

        # Shutdown communicators and buffer
        await self.communicator.shutdown()

        # Initialise all the send/receive counters.
        total_bytes_sent = 0
        msg_send_counter = 0
        total_bytes_recv = 0
        msg_recv_counter = 0
        # Log the client network usage and accumulate the total network usage.
        for client in self._clients.values():
            client.log_network_usage()

            total_bytes_sent += client.total_bytes_sent
            msg_send_counter += client.msg_send_counter
            total_bytes_recv += client.total_bytes_recv
            msg_recv_counter += client.msg_recv_counter

        # Log the total network usage
        logger.info(
            f"Pool shutdown.\n"
            f"Total bytes sent: {total_bytes_sent}\n"
            f"Total messages sent: {msg_send_counter}\n"
            f"Total bytes received: {total_bytes_recv}\n"
            f"Total messages received: {msg_recv_counter}"
        )

    @override
    async def __aenter__(self) -> Pool:
        """
        Enter the runtime context for the Pool, running the `initialize`
        method.

        :return: The Pool object.
        """
        # Call initialize and shutdown
        await self.initialize()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """
        Exit the runtime context for the Pool, running the `shutdown` method.

        :param exc_type: Exception type.
        :param exc_val: Exception value.
        :param exc_tb: Exception traceback.
        """
        await self.shutdown()
        return False
