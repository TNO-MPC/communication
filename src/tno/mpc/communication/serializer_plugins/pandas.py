"""
(De)serialization logic for pandas objects.
"""

# pylint: disable=unused-argument

from __future__ import annotations

import datetime
import io
import sys
import warnings
from typing import Any, Callable, cast

from tno.mpc.communication import Serializer
from tno.mpc.communication.exceptions import OptionalImportError
from tno.mpc.communication.functions import (
    redirect_importerror_oserror_to_optionalimporterror,
)
from tno.mpc.communication.packers import DeserializerOpts, SerializerOpts

with redirect_importerror_oserror_to_optionalimporterror():
    import numpy as np
    import pandas as pandas  # not as 'pd', as that messes up serialization._get_signature for Python 3.9
    from packaging.version import parse
    from pandas import DataFrame, Series

try:
    with redirect_importerror_oserror_to_optionalimporterror():
        from pyarrow import ArrowInvalid
except OptionalImportError:

    class ArrowInvalid(Exception):  # type: ignore[no-redef]
        """Dummy exception class in case pyarrow is unavailable."""


ARROW_SUPPORTED_TYPES = (
    bool,
    datetime.datetime,
    float,
    int,
    type(None),  # https://stackoverflow.com/a/41928862
    np.number,
    str,
)
TEMP_COLUMN_NAME = "TNO_MPC_COMMUNICATION_TEMPNAME"
# pandas 2.1.0 deprecates applymap
DF_MAPPING_METHOD = "map" if parse(pandas.__version__) >= parse("2.1.0") else "applymap"


def pandas_serialize_dataframe(
    obj: DataFrame,
    opts: SerializerOpts,
) -> bytes | dict[str, Any]:
    """
    Function for serializing pandas dataframes

    Attempt to use parquet for smaller serialized dataframe, but fallback to dictionaries
    otherwise.

    :param obj: pandas object to serialize
    :param opts: options to change the behaviour of the serialization.
    :raises ValueError: Column names are not of type <str>.
    :return: serialized dataframe
    """

    try:  # Attempt to serialize with parquet
        return obj.to_parquet()
    except ImportError:
        warnings.warn(
            "Package tno.mpc.communication more efficiently serializes pandas objects (with "
            "built-in type elements) with parquet, which requires additional dependencies. Please "
            "consider installing tno.mpc.communication[pandas]."
        )
    except (ArrowInvalid, OverflowError):
        # Object contains unsupported types. We serialize these and let parquet do the rest.
        max_int_bit_length = sys.maxsize.bit_length()
        is_parquet_serializable: Callable[[Any], bool] = lambda x: (
            isinstance(x, ARROW_SUPPORTED_TYPES)
            and not (isinstance(x, int) and x.bit_length() > max_int_bit_length)
        )
        obj_partially_serialized: pandas.DataFrame = getattr(obj, DF_MAPPING_METHOD)(
            lambda x: (
                x
                if is_parquet_serializable(x)
                else Serializer.transform_into_native(x, opts=opts)
            ),
        )
        try:
            return obj_partially_serialized.to_parquet()
        except ArrowInvalid:
            pass
    except (
        ValueError
    ) as exc:  # Turn a very specific exception into a warnings, reraise unperturbed otherwise.
        if "string column" in exc.args[0]:  # Parquet requires string column names.
            warnings.warn(
                "Failed to serialize a pandas object with parquet as the column names are not of "
                "type <str>. This might be resolved by using "
                "'df.columns = df.columns.astype(str)'. Falling back to serialization via "
                "dictionary."
            )
        else:
            raise exc
    # Fall-back to dictionary serialization
    return cast(dict[str, Any], obj.to_dict(orient="split"))


def pandas_deserialize_dataframe(
    obj: bytes | dict[str, Any],
    opts: DeserializerOpts,
) -> DataFrame:
    """
    Function for deserializing pandas dataframe

    :param obj: pandas dataframe to deserialize
    :param opts: options to change the behaviour of the serialization.
    :raise ImportError: Object was serialized with parquet, but required dependencies for
        deserialization are missing.
    :return: deserialized dataframe
    """
    if isinstance(obj, bytes):
        try:
            dataframe = pandas.read_parquet(io.BytesIO(obj))
        except ImportError as exc:
            raise ImportError(
                "The pandas object was serialized to parquet, but the required dependencies for "
                "deserializing this format are missing. Please install "
                "tno.mpc.communication[pandas]."
            ) from exc
    else:  # Dataframe is serialized as dictionary
        dataframe = pandas.DataFrame(**obj)
    fully_deserialized_df: pandas.DataFrame = getattr(dataframe, DF_MAPPING_METHOD)(
        lambda x: (
            Serializer.transform_into_nonnative(x, opts)
            if isinstance(x, dict) and "type" in x and "data" in x
            else x
        )
    )
    return fully_deserialized_df


def pandas_serialize_series(
    obj: Series,
    opts: SerializerOpts,
) -> bytes | dict[str, Any]:
    """
    Function for serializing pandas series

    :param obj: pandas series to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: serialized series
    """
    if obj.name is None:
        return pandas_serialize_dataframe(
            pandas.DataFrame(obj, columns=[TEMP_COLUMN_NAME]),
            opts,
        )
    return pandas_serialize_dataframe(pandas.DataFrame(obj), opts)


def pandas_deserialize_series(
    obj: bytes | dict[str, Any],
    opts: DeserializerOpts,
) -> Series:
    """
    Function for deserializing pandas series

    :param obj: pandas series to deserialize
    :param opts: options to change the behaviour of the serialization.
    :return: deserialized series
    """
    dataframe = pandas_deserialize_dataframe(obj, opts)
    series = dataframe.iloc[:, 0]
    if series.name == TEMP_COLUMN_NAME:
        series.name = None
    return series


def pandas_serialize_timestamp(
    obj: pandas.Timestamp,
    opts: SerializerOpts,
) -> str:
    """
    Function for serializing pandas timestamp

    :param obj: pandas timestamp to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: serialized timestamp
    """
    return obj.to_pydatetime().isoformat()


def pandas_deserialize_timestamp(obj: str, opts: DeserializerOpts) -> pandas.Timestamp:
    """
    Function for deserializing pandas timestamp

    :param obj: pandas timestamp to deserialize
    :param opts: options to change the behaviour of the serialization.
    :return: deserialized timestamp
    """
    return pandas.Timestamp(obj)


def register() -> None:
    """
    Register pandas serializer and deserializer.
    """
    Serializer.register(
        pandas_serialize_dataframe,
        pandas_deserialize_dataframe,
        pandas.DataFrame.__name__,
    )
    Serializer.register(
        pandas_serialize_series, pandas_deserialize_series, pandas.Series.__name__
    )
    Serializer.register(
        pandas_serialize_timestamp,
        pandas_deserialize_timestamp,
        pandas.Timestamp.__name__,
    )
