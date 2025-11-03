"""
(De)serialization logic for gmpy objects.
"""

# pylint: disable=unused-argument
from __future__ import annotations

from typing import TYPE_CHECKING, Union

from tno.mpc.communication import Serializer
from tno.mpc.communication.functions import (
    redirect_importerror_oserror_to_optionalimporterror,
)
from tno.mpc.communication.packers import DeserializerOpts, SerializerOpts

with redirect_importerror_oserror_to_optionalimporterror():
    import gmpy2


if TYPE_CHECKING:
    from typeguard import typeguard_ignore as typeguard_ignore
else:
    from typing import no_type_check as typeguard_ignore


GmpyTypes = Union["gmpy2.xmpz", "gmpy2.mpz", "gmpy2.mpfr", "gmpy2.mpq", "gmpy2.mpc"]


@typeguard_ignore
def gmpy_serialize(
    obj: GmpyTypes,
    opts: SerializerOpts,
) -> bytes:
    """
    Function for serializing gmpy objects

    :param obj: gmpy object to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: serialized object
    """
    return gmpy2.to_binary(obj)


@typeguard_ignore
def gmpy_deserialize(obj: bytes, opts: DeserializerOpts) -> GmpyTypes:
    """
    Function for deserializing gmpy objects

    :param obj: object to deserialize
    :param opts: options to change the behaviour of the serialization.
    :return: deserialized gmpy object
    """
    return gmpy2.from_binary(obj)


def register() -> None:
    """
    Register gmpy2 types serializer and deserializer.
    """
    gmpy_types = ("xmpz", "mpz", "mpfr", "mpq", "mpc")
    Serializer.register(
        gmpy_serialize, gmpy_deserialize, *gmpy_types, check_annotations=False
    )
