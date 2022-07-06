"""
This module tests packing and unpacking of objects
(serialization/deserialization) when gmpy is installed
"""

import pytest

pytest.importorskip("gmpy2")
import gmpy2
import numpy as np
import ormsgpack

from tno.mpc.communication.serialization import GmpyTypes, typeguard_ignore
from tno.mpc.communication.test.test_packing import pack_unpack_test


@typeguard_ignore
@pytest.mark.parametrize(
    "obj",
    [
        gmpy2.xmpz(10),
        gmpy2.mpz(10),
        gmpy2.mpfr(10.0),
        gmpy2.mpq(10, 3),
        gmpy2.mpc("10+3j"),
    ],
)
def test_gmpy_serialization(obj: GmpyTypes) -> None:
    """
    Tests packing and unpacking of gmpy object

    :param obj: gmpy object to pack/unpack
    """
    pack_unpack_test(obj)


def test_gmpy_serialization_list() -> None:
    """
    Tests packing and unpacking of gmpy list object
    """
    pack_unpack_test([gmpy2.mpz(2**2048)] * 42)


def test_gmpy_serialization_dict() -> None:
    """
    Tests packing and unpacking of gmpy list object
    """
    pack_unpack_test({"a": gmpy2.mpz(2**2048), "b": gmpy2.mpfr(42.1231)})


def test_gmpy_serialization_numpy() -> None:
    """
    Tests packing and unpacking of gmpy list object
    """
    pack_unpack_test(
        np.array([gmpy2.mpz(2**2048)] * 42),
        np.array_equal,
        serial_option=ormsgpack.OPT_SERIALIZE_NUMPY,
    )


def test_gmpy_serialization_numpy_ndarray() -> None:
    """
    Tests packing and unpacking of gmpy list object
    """
    pack_unpack_test(
        np.array([[gmpy2.mpz(2**2048)] * 42] * 3),
        np.array_equal,
        serial_option=ormsgpack.OPT_SERIALIZE_NUMPY,
    )
