"""
(De)serialization logic for bitarray objects.
"""
from typing import Any

from tno.mpc.communication.functions import redirect_importerror_to_optionalimporterror
from tno.mpc.communication.serialization import Serialization

with redirect_importerror_to_optionalimporterror():
    import bitarray
    import bitarray.util


def bitarray_serialize(obj: bitarray.bitarray, **_kwargs: Any) -> bytes:
    r"""
    Function for serializing bitarray

    :param obj: bitarray object to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized object
    """
    return bitarray.util.serialize(obj)


def bitarray_deserialize(obj: bytes, **_kwargs: Any) -> bitarray.bitarray:
    r"""
    Function for deserializing bitarrays

    :param obj: object to deserialize
    :param \**_kwargs: optional extra keyword arguments
    :return: deserialized bitarray object
    """
    return bitarray.util.deserialize(obj)


def register() -> None:
    """
    Register bitarray serializer and deserializer.
    """
    Serialization.register(
        bitarray_serialize, bitarray_deserialize, bitarray.bitarray.__name__
    )
