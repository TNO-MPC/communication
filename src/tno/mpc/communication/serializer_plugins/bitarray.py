"""
(De)serialization logic for bitarray objects.
"""

# pylint: disable=unused-argument
from __future__ import annotations

from tno.mpc.communication import Serializer
from tno.mpc.communication.functions import (
    redirect_importerror_oserror_to_optionalimporterror,
)
from tno.mpc.communication.packers import DeserializerOpts, SerializerOpts

with redirect_importerror_oserror_to_optionalimporterror():
    import bitarray
    import bitarray.util


def bitarray_serialize(
    obj: bitarray.bitarray,
    opts: SerializerOpts,
) -> bytes:
    """
    Function for serializing bitarray

    :param obj: bitarray object to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: serialized object
    """
    return bitarray.util.serialize(obj)


def bitarray_deserialize(obj: bytes, opts: DeserializerOpts) -> bitarray.bitarray:
    """
    Function for deserializing bitarrays

    :param obj: object to deserialize
    :param opts: options to change the behaviour of the serialization.
    :return: deserialized bitarray object
    """
    return bitarray.util.deserialize(obj)


def register() -> None:
    """
    Register bitarray serializer and deserializer.
    """
    Serializer.register(
        bitarray_serialize,
        bitarray_deserialize,
        bitarray.bitarray.__name__,
    )
