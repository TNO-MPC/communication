"""
This module contains the abstract classes for Communicators and Clients.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from enum import IntEnum, auto
from typing import Callable, Generic, TypeVar

logger = logging.getLogger(__name__)


# Types
Connection = TypeVar("Connection")
ReceiveHandlerType = Callable[[str, bytes], Awaitable[None]]


# State
class CommunicatorState(IntEnum):
    """
    The states in the lifecycle of a `Communicator.`

    Upon construction, the Communicator is in the `UNINITIALIZED` state. To
    start the Communicator, `Communicator.initialize` must be called,
    transitioning the Communicator to the `STARTED` state. To stop the
    Communicator, `Communicator.shutdown` must be called, transitioning the
    Communicator to the `STOPPED` state.
    """

    UNINITIALIZED = auto()
    STARTED = auto()
    STOPPED = auto()


class IllegalStateAction(Exception):
    """
    Exception class for when an action is performed that is illegal in the current state.
    """

    def __init__(self, action: str, curr_state: CommunicatorState) -> None:
        super().__init__(
            f"Illegal: Cannot perform '{action}' while state is {curr_state.name}."
        )


class Communicator(Generic[Connection], ABC):
    """
    An abstract interface for sending and receiving packets of bytes to
    registered connections.

    A Communicator has "connections" which describe how to reach a specific
    endpoint. These connections are added through
    `Communicator.add_connection`. Each connection has a unique name, which is
    used to address the connection when sending packets to it, or to identify
    the connection when receiving packets from it.

    To be able to receive packets from connections through the Communicator,
    one must register a `receive_handler` using
    `Communicator.register_receive_handler`. This `receive_handler` is called
    for each packet that is received.
    """

    def __init__(self) -> None:
        """
        Initializer for the Communicator.
        """
        self._receive_handler: ReceiveHandlerType | None = None
        self._connections: dict[str, Connection] = {}
        self._state = CommunicatorState.UNINITIALIZED

    def set_receive_handler(self, receive_handler: ReceiveHandlerType) -> None:
        """
        Register the `receive_handler` to be called upon receiving a message.

        :param receive_handler:
        """
        self._receive_handler = receive_handler

    @property
    def receive_handler(self) -> ReceiveHandlerType:
        """
        The handler to be called upon receiving a new packet.

        :raise AttributeError: If no receive_handler is set.
        :return: A handler function which accepts packets.
        """
        if self._receive_handler is None:
            raise AttributeError("The receive handler is not set.")
        return self._receive_handler

    def add_connection(self, name: str, connection: Connection) -> None:
        """
        Register a new connection to the communicator.

        By registering a connection to the communicator, the communicator can
        send and receive messages through the connection. Each connection needs
        to be identified by a unique `name`.

        :param name: The name of the connection to register.
        :param connection: The connection to register.
        :raise IllegalStateAction: If the state is not INITIALIZED
        :raise KeyError: If a connection with the given name already exists.
        """
        if not self._state == CommunicatorState.UNINITIALIZED:
            raise IllegalStateAction("add_connection", self._state)
        if name in self._connections:
            raise KeyError(f"Connection with name '{name}' already registered!")

        self._connections[name] = connection

    async def initialize(self) -> None:
        """
        Initialize and start the Communicator.

        Functionality depends on implementation, but often some (asynchronous)
        setup steps are required to setup the connections.

        :raise IllegalStateAction: If the state is not UNINITIALIZED.
        """
        if not self._state == CommunicatorState.UNINITIALIZED:
            raise IllegalStateAction("start", self._state)
        self._state = CommunicatorState.STARTED

        await self._initialize()

    @abstractmethod
    async def _initialize(self) -> None: ...

    async def send(self, recipient: str, packet: bytes) -> None:
        """
        Send a message `packet` to the `recipient`.

        :param recipient: The intended recipient of the message.
        :param packet: The message to send to the recipient.
        :raise IllegalStateAction: If the state is not STARTED.
        :raise KeyError: If no connection is registered with the given name.
        """
        if not self._state == CommunicatorState.STARTED:
            raise IllegalStateAction("send", self._state)
        if not recipient in self._connections:
            raise KeyError(f"No connection registered with name '{recipient}'")

        await self._send(self._connections[recipient], packet)

    @abstractmethod
    async def _send(self, recipient: Connection, packet: bytes) -> None: ...

    async def shutdown(self) -> None:
        """
        Shutdown the communicator.

        :raise IllegalStateAction: If the state is not STARTED
        """
        if not self._state == CommunicatorState.STARTED:
            raise IllegalStateAction("shutdown", self._state)
        self._state = CommunicatorState.STOPPED

        await self._shutdown()

    @abstractmethod
    async def _shutdown(self) -> None: ...
