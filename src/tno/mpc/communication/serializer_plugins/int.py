"""
(De)serialization logic for int.
"""
from typing import Any

from tno.mpc.communication.serialization import Serialization


def int_serialize(obj: int, **_kwargs: Any) -> bytes:
    r"""
    Function for serializing Python ints

    :param obj: int object to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized object
    """
    return obj.to_bytes((obj.bit_length() + 8) // 8, "little", signed=True)


def int_deserialize(obj: bytes, **_kwargs: Any) -> int:
    r"""
    Function for deserializing Python ints

    :param obj: object to deserialize
    :param \**_kwargs: optional extra keyword arguments
    :return: deserialized int object
    """
    return int.from_bytes(obj, "little", signed=True)


def register() -> None:
    """
    Register int serializer and deserializer.
    """
    Serialization.register(int_serialize, int_deserialize, int.__name__)
