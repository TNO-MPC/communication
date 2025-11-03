"""
(De)serialization logic for tuple.
"""

# pylint: disable=unused-argument

from __future__ import annotations

from typing import Any

from tno.mpc.communication import Serializer
from tno.mpc.communication.packers import DeserializerOpts, SerializerOpts


def tuple_serialize(
    obj: tuple[Any, ...],
    opts: SerializerOpts,
) -> list[Any]:
    """
    Function for serializing tuples

    :param obj: tuple object to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: serialized object
    """
    return list(obj)


def tuple_deserialize(obj: list[Any], opts: DeserializerOpts) -> tuple[Any, ...]:
    """
    Function for deserializing tuples

    :param obj: object to deserialize
    :param opts: options to change the behaviour of the serialization.
    :return: deserialized tuple object
    """
    return tuple(Serializer.transform_into_nonnative(obj, opts))


def register() -> None:
    """
    Register tuple serializer and deserializer.
    """
    Serializer.register(
        tuple_serialize, tuple_deserialize, tuple.__name__, check_annotations=False
    )
