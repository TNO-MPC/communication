"""
This module contains a Buffer class for storing incoming or expected messages.
"""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Buffer(Generic[T]):
    """
    A class to store messages in buffers for clients. It stores elements of a type T.
    """

    def __init__(self) -> None:
        """
        Initialise an empty buffer.
        """
        self._buffer_per_client: dict[str, dict[str, T]] = {}

    def add_client(self, client_name: str) -> None:
        """
        Add a new buffer for a client with name client_name.

        :param client_name: The name of the client to add.
        :raise ValueError: When a buffer already exists for the client.
        """
        if client_name in self._buffer_per_client:
            raise ValueError(
                f"A buffer already exists for client with name '{client_name}'"
            )
        self._buffer_per_client[client_name] = {}

    def push(self, client_name: str, msg_id: str, content: T) -> None:
        """
        Add a message for a client to the buffer.

        :param client_name: the client under which to store the message.
        :param msg_id: The message identifier.
        :param content: The content of the message.
        :raise KeyError: If no buffer exists for the given client.
        :raise AttributeError: If a message with msg_id already exists in the buffer.
        """
        buffer = self.get_client(client_name)
        if msg_id in buffer:
            raise AttributeError(
                "A message with this id is already present in the buffer."
            )
        self._buffer_per_client[client_name][msg_id] = content

    def has_buffer(self, client_name: str) -> bool:
        """
        Whether a buffer exists for the given client.

        :param client_name: The name of the client to check for.
        :return: Whether a buffer exists for the given client.
        """
        return client_name in self._buffer_per_client

    def has_message(self, client_name: str, msg_id: str | None = None) -> bool:
        """
        Whether a message with given id is present in the buffer for the given
        client. If no message id is specified, it returns whether any message
        is in the buffer for the given client.

        :param client_name: The client to check for.
        :param msg_id: The message id to check the existence for.
            If None, it will check whether any message is available for the
            given client.
        :return: Boolean indicating whether the given / any message is
            available for the client.
        """
        if msg_id:
            return msg_id in self._buffer_per_client[client_name]
        return bool(self._buffer_per_client[client_name])

    def pop(self, client_name: str, msg_id: str) -> T:
        """
        Pop a message with given id from the client's buffer.

        :param client_name: The client for which the message must be popped.
        :param msg_id: The identifier for the message.
        :raise KeyError: If no buffer exists for the given client.
        :raise KeyError: If the message with given ID does not exist.
        :return: The content of the message.
        """
        return self.get_client(client_name).pop(msg_id)

    def get_client(self, client_name: str) -> dict[str, T]:
        """
        Return the buffer for the given client.

        :param client_name: The name of the client for which to return the
            buffer.
        :raise KeyError: If the specified client does not have a buffer.
        :return: Either the specified buffer or all the buffers.
        """
        if not self.has_buffer(client_name):
            raise KeyError("No buffer exists for the given client.")
        return self._buffer_per_client[client_name]

    def empty(self, client_name: str | None = None) -> None:
        """
        Clear the buffer for the given client. If no client is specified, clear
        all buffers. If the client does not have a buffer, a new buffer will be
        created.

        :param client_name: If specified, clear the buffer for this client. If
            not specified, clear all buffers.
        """
        if client_name is not None:
            self._buffer_per_client[client_name] = {}
            return

        for _client_name in self._buffer_per_client:
            self._buffer_per_client[_client_name] = {}
