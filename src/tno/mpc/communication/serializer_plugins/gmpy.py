"""
(De)serialization logic for gmpy objects.
"""
from typing import TYPE_CHECKING, Any, Union

from tno.mpc.communication.functions import redirect_importerror_to_optionalimporterror
from tno.mpc.communication.serialization import Serialization

with redirect_importerror_to_optionalimporterror():
    import gmpy2


if TYPE_CHECKING:
    from typeguard import typeguard_ignore as typeguard_ignore
else:
    from typing import no_type_check as typeguard_ignore


GmpyTypes = Union["gmpy2.xmpz", "gmpy2.mpz", "gmpy2.mpfr", "gmpy2.mpq", "gmpy2.mpc"]


@typeguard_ignore  # pylint: disable=used-before-assignment
def gmpy_serialize(obj: GmpyTypes, **_kwargs: Any) -> bytes:
    r"""
    Function for serializing gmpy objects

    :param obj: gmpy object to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized object
    """
    return gmpy2.to_binary(obj)


@typeguard_ignore
def gmpy_deserialize(obj: bytes, **_kwargs: Any) -> GmpyTypes:
    r"""
    Function for deserializing gmpy objects

    :param obj: object to deserialize
    :param \**_kwargs: optional extra keyword arguments
    :return: deserialized gmpy object
    """
    return gmpy2.from_binary(obj)


def register() -> None:
    """
    Register gmpy2 types serializer and deserializer.
    """
    gmpy_types = ("xmpz", "mpz", "mpfr", "mpq", "mpc")
    Serialization.register(
        gmpy_serialize, gmpy_deserialize, *gmpy_types, check_annotations=False
    )
