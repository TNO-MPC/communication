"""
(De)serialization logic for pytorch objects.
"""

from __future__ import annotations

from typing import Any

from tno.mpc.communication.functions import (
    redirect_importerror_oserror_to_optionalimporterror,
)
from tno.mpc.communication.serialization import Serialization

with redirect_importerror_oserror_to_optionalimporterror():
    import torch
    from safetensors.torch import load, save
    from torch import Tensor

TENSOR_KEY = "my_tensor"


def torch_serialize_tensor(obj: Tensor, **_kwargs: Any) -> tuple[int, ...] | bytes:
    r"""
    Function for serializing pytorch tensors

    :param obj: pytorch object to serialize
    :param \**_kwargs: optional extra keyword arguments
    :return: serialized tensor
    """
    if obj.numel() == 0:  # empty tensor
        return tuple(obj.size())
    return save({TENSOR_KEY: obj})


def torch_deserialize_tensor(obj: dict[str, Any] | bytes, **_kwargs: Any) -> Tensor:
    r"""
    Function for deserializing pytorch tensors and loading them into cpu

    :param obj: pytorch tensor to deserialize
    :param \**_kwargs: optional extra keyword arguments
    :return: deserialized tensor
    """
    if isinstance(obj, dict):
        dims = Serialization.deserialize(obj)
        return torch.tensor([]).reshape(dims)
    return load(obj)[TENSOR_KEY]


def register() -> None:
    """
    Register pytorch serializer and deserializer.
    """
    Serialization.register(
        torch_serialize_tensor,
        torch_deserialize_tensor,
        torch.Tensor.__name__,
        check_annotations=False,
    )
