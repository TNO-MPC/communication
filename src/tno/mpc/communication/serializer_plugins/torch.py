"""
(De)serialization logic for pytorch objects.
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
    import torch
    from safetensors.torch import load, save
    from torch import Tensor

TENSOR_KEY = "my_tensor"


def torch_serialize_tensor(
    obj: Tensor,
    opts: SerializerOpts,
) -> tuple[int, ...] | bytes:
    """
    Function for serializing pytorch tensors

    :param obj: pytorch object to serialize
    :param opts: options to change the behaviour of the serialization.
    :return: serialized tensor
    """
    if obj.numel() == 0:  # empty tensor
        return tuple(obj.size())
    return save({TENSOR_KEY: obj})


def torch_deserialize_tensor(
    obj: dict[str, Any] | bytes,
    opts: DeserializerOpts,
) -> Tensor:
    r"""
    Function for deserializing pytorch tensors and loading them into cpu

    :param obj: pytorch tensor to deserialize
    :param opts: options to change the behaviour of the serialization.
    :return: deserialized tensor
    """
    if isinstance(obj, dict):
        dims = Serializer.transform_into_nonnative(obj, opts=opts)
        return torch.tensor([]).reshape(dims)
    return load(obj)[TENSOR_KEY]


def register() -> None:
    """
    Register pytorch serializer and deserializer.
    """
    Serializer.register(
        torch_serialize_tensor,
        torch_deserialize_tensor,
        torch.Tensor.__name__,
        check_annotations=False,
    )
