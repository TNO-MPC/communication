"""
(De)serialization logic for numpy objects.
"""
from typing import Any, Dict, List

from tno.mpc.communication.functions import redirect_importerror_to_optionalimporterror
from tno.mpc.communication.serialization import Serialization

with redirect_importerror_to_optionalimporterror():
    import numpy as np
    import numpy.typing as npt


def numpy_serialize(obj: npt.NDArray[Any], **_kwargs: Any) -> Dict[str, List[Any]]:
    r"""
    Function for serializing numpy object arrays

    :param obj: numpy object to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized object
    """
    return {"values": obj.tolist(), "shape": [obj.shape]}


def numpy_deserialize(
    obj: Dict[str, List[Any]], **kwargs: Any
) -> npt.NDArray[np.object_]:
    r"""
    Function for serializing numpy object arrays

    :param obj: numpy object to serialize
    :param \**kwargs: optional extra keyword arguments
    :return: deserialized object
    """
    # ormsgpack can handle native numpy dtypes
    result: npt.NDArray[np.object_] = np.empty(obj["shape"][0], dtype=object)
    if obj["values"]:
        result[:] = Serialization.collection_deserialize(obj["values"], **kwargs)
    return result


def register() -> None:
    """
    Register numpy serializer and deserializer.
    """
    Serialization.register(
        numpy_serialize,
        numpy_deserialize,
        "ndarray",
    )
