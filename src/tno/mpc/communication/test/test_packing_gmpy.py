"""
This module tests packing and unpacking of objects
(serialization/deserialization) when gmpy is installed
"""
# pylint: disable=wrong-import-position

import pandas as pd
import pytest

pytest.importorskip("gmpy2")
import gmpy2
import numpy as np
import ormsgpack

from tno.mpc.communication.serializer_plugins.gmpy import GmpyTypes, typeguard_ignore
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


def test_gmpy_serialization_pandas_series() -> None:
    """
    Tests packing and unpacking of a pandas series
    """
    dataframe = pd.Series(list(map(gmpy2.mpz, (1, 2, 3))), index=["a", "b", "c"])
    pack_unpack_test(dataframe, lambda df1, df2: df1.equals(df2))


def test_gmpy_serialization_pandas_dataframe() -> None:
    """
    Tests packing and unpacking of a pandas dataframe containing gmpy and string values
    """
    dataframe = pd.DataFrame(
        {"key1": list(map(gmpy2.mpz, (1, 2, 3))), "key2": "str_value"},
        index=["a", "b", "c"],
    )
    pack_unpack_test(dataframe, lambda df1, df2: df1.equals(df2))
