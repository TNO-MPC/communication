"""
(De)serialization logic for int.
"""

# pylint: disable=unused-argument
from __future__ import annotations

from tno.mpc.communication import Serializer
from tno.mpc.communication.packers import DeserializerOpts, SerializerOpts


def int_serialize(
    obj: int,
    opts: SerializerOpts,
) -> bytes:
    """
    Function for serializing Python ints

    :param obj: int object to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: serialized object
    """
    return obj.to_bytes((obj.bit_length() + 8) // 8, "little", signed=True)


def int_deserialize(obj: bytes, opts: DeserializerOpts) -> int:
    """
    Function for deserializing Python ints

    :param obj: object to deserialize
    :param opts: options to change the behaviour of the serialization.
    :return: deserialized int object
    """
    return int.from_bytes(obj, "little", signed=True)


def register() -> None:
    """
    Register int serializer and deserializer.
    """
    Serializer.register(int_serialize, int_deserialize, int.__name__)
