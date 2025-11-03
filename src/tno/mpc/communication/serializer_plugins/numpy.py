"""
(De)serialization logic for numpy objects. Used only when
ormsgpack.packb(..., option=(ormsgpack.OPT_SERIALIZE_NUMPY, ...)) fails.
"""

# pylint: disable=unused-argument

from __future__ import annotations

from typing import Any

from tno.mpc.communication import Serializer
from tno.mpc.communication.functions import (
    redirect_importerror_oserror_to_optionalimporterror,
)
from tno.mpc.communication.packers import DeserializerOpts, SerializerOpts

with redirect_importerror_oserror_to_optionalimporterror():
    import numpy as np
    import numpy.typing as npt


# called only if ormsgpack fails serializing (see module docstring)
def numpy_serialize(
    obj: npt.NDArray[Any],
    opts: SerializerOpts,
) -> dict[str, Any]:
    """
    Function for serializing numpy object arrays

    :param obj: numpy object to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: serialized object
    """
    return {"values": obj.tolist(), "shape": obj.shape}


def numpy_deserialize(
    obj: dict[str, Any], opts: DeserializerOpts
) -> npt.NDArray[np.object_]:
    """
    Function for serializing numpy object arrays

    :param obj: numpy object to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: deserialized object
    """
    # ormsgpack can handle native numpy dtypes
    obj_dict = Serializer.transform_into_nonnative(obj, opts)
    if not obj_dict["shape"]:
        return np.array(obj_dict["values"])

    result: npt.NDArray[np.object_] = np.empty(obj_dict["shape"], dtype=object)
    if obj_dict["values"]:
        result[:] = obj_dict["values"]
    return result


def register() -> None:
    """
    Register numpy serializer and deserializer.
    """
    Serializer.register(
        numpy_serialize, numpy_deserialize, np.ndarray.__name__, check_annotations=False
    )
