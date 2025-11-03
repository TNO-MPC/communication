"""
Provides a generic interface for packing and unpacking messages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from tno.mpc.communication.packers.serialization import (
    DefaultDeserializerOpts,
    DefaultSerializerOpts,
    DeserializerOpts,
    Serializer,
    SerializerOpts,
)


class Packer(ABC):
    """
    Pack a message into bytes for sending it to a peer.
    """

    @abstractmethod
    def pack(self, content: Any, msg_id: str) -> bytes:
        """
        Pack the message with given content and message id.

        :param content: The content of the message.
        :param msg_id: The message identifier.
        :return: The resulting packet.
        """

    @abstractmethod
    def pack_multiple(
        self,
        content: Any,
        msg_ids: Iterable[str],
    ) -> tuple[bytes, ...]:
        """
        Pack the message with given content and for every message id.

        :param content: The content of the message.
        :param msg_ids: The message identifiers.
        :return: The resulting packet.
        """

    @abstractmethod
    def unpack(self, packet: bytes) -> tuple[str, Any]:
        """
        Unpack a packet into a message id and content.

        :param packet: The packed packet.
        :return: Tuple containing the message id and the content of the packet.
        """


class DefaultPacker(Packer):
    """
    The packer that uses the default serializer.
    """

    def __init__(
        self,
        serializer_opts: SerializerOpts = DefaultSerializerOpts,
        deserializer_opts: DeserializerOpts = DefaultDeserializerOpts,
    ):
        """
        Initialise the packer.

        :param serializer_opts: Options to change the behaviour of serialization.
        :param deserializer_opts: Options to change the behaviour of deserialization.
        """
        self.serializer_opts = serializer_opts
        self.deserializer_opts = deserializer_opts

    def pack(self, content: Any, msg_id: str) -> bytes:
        """
        Pack the message with given content and message id.

        :param content: The content of the message.
        :param msg_id: The message identifier.
        :return: The resulting packet.
        """
        packed_content = Serializer.serialize(obj=content, opts=self.serializer_opts)
        return Serializer.serialize(
            obj={"object": packed_content, "id": msg_id},
            opts=self.serializer_opts,
        )

    def pack_multiple(
        self,
        content: Any,
        msg_ids: Iterable[str],
    ) -> tuple[bytes, ...]:
        """
        Pack the message with given content and for every message id.

        :param content: The content of the message.
        :param msg_ids: The message identifiers.
        :return: The resulting packet.
        """
        packed_content = Serializer.serialize(obj=content, opts=self.serializer_opts)
        return tuple(
            Serializer.serialize(
                obj={"object": packed_content, "id": id_}, opts=self.serializer_opts
            )
            for id_ in msg_ids
        )

    def unpack(self, packet: bytes) -> tuple[str, Any]:
        """
        Unpack a packet into a message id and content.

        :param packet: The packed packet.
        :raise ValueError: If the deserialized packet does not contain the expected keys.
        :return: Tuple containing the message id and the content of the packet.
        """
        msg: dict[str, Any] = Serializer.deserialize(
            obj=packet, opts=self.deserializer_opts
        )
        if not msg.keys() == {"id", "object"}:
            raise ValueError(
                f"Expected deserialized packet to contain keys 'id' and 'object', "
                f"but found keys: {','.join(msg.keys())}"
            )
        content = Serializer.deserialize(obj=msg["object"], opts=self.deserializer_opts)
        return msg["id"], content
