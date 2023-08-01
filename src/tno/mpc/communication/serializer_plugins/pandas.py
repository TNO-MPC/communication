"""
(De)serialization logic for pandas objects.
"""
from __future__ import annotations

import datetime
import io
import sys
import warnings
from typing import Any, Callable, Dict, cast

from tno.mpc.communication.functions import redirect_importerror_to_optionalimporterror
from tno.mpc.communication.serialization import Serialization

with redirect_importerror_to_optionalimporterror():
    import numpy as np
    import pandas as pd
    from pandas import DataFrame, Series

try:
    from pyarrow import ArrowInvalid
except ImportError:

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


def pandas_serialize_dataframe(  # pylint: disable=missing-raises-doc
    obj: DataFrame, use_pickle: bool, **kwargs: Any
) -> bytes | dict[str, Any]:
    r"""
    Function for serializing pandas dataframes

    Attempt to use parquet for smaller serialized dataframe, but fallback to dictionaries
    otherwise.

    :param obj: pandas object to serialize
    :param use_pickle: set to True to enable serialization fallback to pickle
    :param \**kwargs: optional extra keyword arguments
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
        obj_partially_serialized = obj.applymap(
            lambda x: x
            if is_parquet_serializable(x)
            else Serialization.serialize(x, use_pickle=use_pickle, **kwargs)
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
    return cast(Dict[str, Any], obj.to_dict(orient="split"))


def pandas_deserialize_dataframe(
    obj: bytes | dict[str, Any], use_pickle: bool, **_kwargs: Any
) -> DataFrame:
    r"""
    Function for deserializing pandas dataframe

    :param obj: pandas dataframe to deserialize
    :param use_pickle: set to True to enable serialization fallback to pickle
    :param \**_kwargs: optional extra keyword arguments
    :raise ImportError: Object was serialized with parquet, but required dependencies for
        deserialization are missing.
    :return: deserialized dataframe
    """
    if isinstance(obj, bytes):
        try:
            dataframe = pd.read_parquet(io.BytesIO(obj))
        except ImportError as exc:
            raise ImportError(
                "The pandas object was serialized to parquet, but the required dependencies for "
                "deserializing this format are missing. Please install "
                "tno.mpc.communication[pandas]."
            ) from exc
    else:  # Dataframe is serialized as dictionary
        dataframe = pd.DataFrame(**obj)
    return dataframe.applymap(
        lambda x: Serialization.deserialize(x, use_pickle=use_pickle)
        if isinstance(x, dict) and "type" in x and "data" in x
        else x
    )


def pandas_serialize_series(obj: Series[Any], **_kwargs: Any) -> bytes | dict[str, Any]:
    r"""
    Function for serializing pandas series

    :param obj: pandas series to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized series
    """
    if obj.name is None:
        return pandas_serialize_dataframe(
            pd.DataFrame(obj, columns=[TEMP_COLUMN_NAME]), **_kwargs
        )
    return pandas_serialize_dataframe(pd.DataFrame(obj), **_kwargs)


def pandas_deserialize_series(
    obj: bytes | dict[str, Any], **kwargs: Any
) -> Series:  # type: ignore[type-arg]
    r"""
    Function for deserializing pandas series

    :param obj: pandas series to deserialize
    :param \**kwargs: optional extra keyword arguments
    :return: deserialized series
    """
    dataframe = pandas_deserialize_dataframe(obj, **kwargs)
    series = dataframe.iloc[:, 0]
    if series.name == TEMP_COLUMN_NAME:
        series.name = None
    return series


def register() -> None:
    """
    Register pandas serializer and deserializer.
    """
    Serialization.register(
        pandas_serialize_dataframe, pandas_deserialize_dataframe, pd.DataFrame.__name__
    )
    Serialization.register(
        pandas_serialize_series, pandas_deserialize_series, pd.Series.__name__
    )
