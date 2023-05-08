"""
(De)serialization logic for numpy objects. Used only when
ormsgpack.packb(..., option=(ormsgpack.OPT_SERIALIZE_NUMPY, ...)) fails.
"""
from __future__ import annotations

from typing import Any

from tno.mpc.communication.functions import redirect_importerror_to_optionalimporterror
from tno.mpc.communication.serialization import Serialization

with redirect_importerror_to_optionalimporterror():
    import numpy as np
    import numpy.typing as npt


# called only if ormsgpack fails serializing (see module docstring)
def numpy_serialize(obj: npt.NDArray[Any], **_kwargs: Any) -> dict[str, Any]:
    r"""
    Function for serializing numpy object arrays

    :param obj: numpy object to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized object
    """
    return {"values": obj.tolist(), "shape": obj.shape}


def numpy_deserialize(
    obj: dict[str, Any], use_pickle: bool, **_kwargs: Any
) -> npt.NDArray[np.object_]:
    r"""
    Function for serializing numpy object arrays

    :param obj: numpy object to serialize
    :param use_pickle: set to True to enable serialization fallback to pickle
    :param \**_kwargs: optional extra keyword arguments
    :return: deserialized object
    """
    # ormsgpack can handle native numpy dtypes
    obj_dict = Serialization.deserialize(obj, use_pickle=use_pickle)
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
    Serialization.register(
        numpy_serialize, numpy_deserialize, np.ndarray.__name__, check_annotations=False
    )
