"""
(De)serialization logic for tuple.
"""
from __future__ import annotations

from typing import Any

from tno.mpc.communication.serialization import Serialization


def tuple_serialize(obj: tuple[Any, ...], **_kwargs: Any) -> list[Any]:
    r"""
    Function for serializing tuples

    :param obj: tuple object to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized object
    """
    return list(obj)


def tuple_deserialize(obj: list[Any], **kwargs: Any) -> tuple[Any, ...]:
    r"""
    Function for deserializing tuples

    :param obj: object to deserialize
    :param \**kwargs: optional extra keyword arguments
    :return: deserialized tuple object
    """
    return tuple(Serialization.collection_deserialize(obj, **kwargs))


def register() -> None:
    """
    Register tuple serializer and deserializer.
    """
    Serialization.register(
        tuple_serialize, tuple_deserialize, tuple.__name__, check_annotations=False
    )
