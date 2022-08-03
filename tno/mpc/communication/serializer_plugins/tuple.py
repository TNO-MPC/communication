"""
(De)serialization logic for tuple.
"""
from typing import Any, List, Tuple

from tno.mpc.communication.serialization import Serialization


def tuple_serialize(obj: Tuple[Any, ...], **_kwargs: Any) -> List[Any]:
    r"""
    Function for serializing tuples

    :param obj: tuple object to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized object
    """
    return list(obj)


def tuple_deserialize(obj: List[Any], **kwargs: Any) -> Tuple[Any, ...]:
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
        tuple_serialize, tuple_deserialize, "tuple", check_annotations=False
    )
