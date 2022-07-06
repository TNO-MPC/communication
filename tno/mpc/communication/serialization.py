"""
This module contains the serialization logic used in sending and receiving arbitrary objects.
"""

from __future__ import annotations

import inspect
import pickle
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import ormsgpack
from mypy_extensions import Arg, KwArg
from typing_extensions import Protocol

from tno.mpc.communication.functions import init

logger = init(__name__)
try:
    import gmpy2

    from tno.mpc.encryption_schemes.utils import USE_GMPY2
except ImportError:
    USE_GMPY2 = False

try:
    import bitarray
    import bitarray.util

    USE_BITARRAY = True
except ImportError:
    USE_BITARRAY = False

try:
    import numpy as np
    import numpy.typing as npt

    USE_NUMPY = True
except ImportError:
    USE_NUMPY = False

if TYPE_CHECKING:
    from typeguard import typeguard_ignore as typeguard_ignore
else:
    from typing import no_type_check as typeguard_ignore

GmpyTypes = Union["gmpy2.xmpz", "gmpy2.mpz", "gmpy2.mpfr", "gmpy2.mpq", "gmpy2.mpc"]

DEFAULT_PACK_OPTION = (
    ormsgpack.OPT_SERIALIZE_NUMPY
    | ormsgpack.OPT_PASSTHROUGH_BIG_INT
    | ormsgpack.OPT_PASSTHROUGH_TUPLE
)


class SupportsSerialization(Protocol):
    """
    Type placeholder for classes supporting custom serialization.
    """

    def serialize(self, **kwargs: Any) -> Any:
        r"""
        Serialize this object into bytes.

        :param \**kwargs: Optional extra keyword arguments.
        :return: Serialization of this instance to Dict with bytes.
        """

    @staticmethod
    def deserialize(obj: Any, **kwargs: Any) -> SupportsSerialization:
        r"""
        Deserialize the given object into an object of this class.

        :param obj: object to be deserialized.
        :param \**kwargs: Optional extra keyword arguments.
        :return: Deserialized object.
        """


StandardT = TypeVar("StandardT", int, float, str)


class Serialization:
    """
    Virtual class that provides packing and unpacking functions used for communications.
    The outline is as follows:
    - serialization functions for different classes
    - packing function that handles metadata and determines which serialization needs to happen

    - deserialization functions for different classes
    - unpacking function that handles metadata and determines which deserialization needs to happen
    """

    # dictionary for serialization functions of classes that are not specified here
    custom_serialization_funcs: ClassVar[
        Dict[
            str,
            Callable[[Arg(SupportsSerialization, "self"), KwArg(Any)], Any],
        ]
    ] = {}
    # dictionary for deserialization functions of classes that are not specified here
    custom_deserialization_funcs: ClassVar[
        Dict[
            str,
            Callable[[Arg(Any, "obj"), KwArg(Any)], SupportsSerialization],
        ]
    ] = {}

    # region serialization functions
    @staticmethod
    def numpy_serialize(obj: npt.NDArray[Any], **_kwargs: Any) -> Dict[str, Any]:
        r"""
        Function for serializing numpy object arrays

        :param obj: numpy object to serialize
        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"values": obj.tolist(), "shape": obj.shape}

    @staticmethod
    def tuple_serialize(obj: Tuple[Any, ...], **_kwargs: Any) -> List[Any]:
        r"""
        Function for serializing tuples

        :param obj: tuple object to serialize
        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return list(obj)

    @staticmethod
    def int_serialize(obj: int, **_kwargs: Any) -> bytes:
        r"""
        Function for serializing Python ints

        :param obj: int object to serialize
        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return obj.to_bytes((obj.bit_length() + 8) // 8, "little", signed=True)

    @staticmethod
    def bitarray_serialize(obj: bitarray.bitarray, **_kwargs: Any) -> bytes:
        r"""
        Function for serializing bitarray

        :param obj: bitarray object to serialize
        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return bitarray.util.serialize(obj)

    @staticmethod
    def default_serialize(obj: Any, use_pickle: bool, **_kwargs: Any) -> bytes:
        r"""
        Fall-back function is case no specific serialization function is available.
        This function uses the pickle library

        :param obj: object to serialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback serializer
        :param \**_kwargs: optional extra keyword arguments
        :raise NotImplementedError: raised when no serialization function is defined for object
        :return: serialized object
        """
        if use_pickle:
            return pickle.dumps(obj)
        # else
        raise NotImplementedError(
            f"There is no serialization function defined for "
            f"{obj.__class__.__name__} objects."
        )

    @staticmethod
    @typeguard_ignore
    def gmpy_serialize(obj: GmpyTypes, **_kwargs: Any) -> bytes:
        r"""
        Function for serializing gmpy objects

        :param obj: gmpy object to serialize
        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return gmpy2.to_binary(obj)

    @staticmethod
    def clear_new_serialization_logic() -> None:
        """
        Clear all custom serialization (and deserialization) logic that was added to this class.
        """
        Serialization.custom_serialization_funcs = {}
        Serialization.custom_deserialization_funcs = {}

    @staticmethod
    def set_serialization_logic(
        obj_class: Type[SupportsSerialization], check_annotations: bool = True
    ) -> None:
        """
        Function for storing serialization logic for classes that have not been specified here or
        need to be overridden

        :param obj_class: object class to set serialization logic for
        :param check_annotations: validate return annotation of the serialization logic
        :raise RepetitionError: raised when serialization function is already defined for object class
        :raise TypeError: raised when provided object class has no (de)serialization function
        :raise AnnotationError: raised when the return annotation is inconsistent
        """
        obj_class_name = obj_class.__name__
        if (
            obj_class_name in Serialization.custom_serialization_funcs
            and obj_class_name in Serialization.custom_deserialization_funcs
        ):
            raise RepetitionError(
                "The serialization logic for this class has already been set"
            )
        serialization_func = obj_class.serialize
        deserialization_func = obj_class.deserialize
        if not callable(serialization_func):
            raise TypeError(
                "the provided class does have a serialize attribute, but it is not a function"
            )
        if not callable(deserialization_func):
            raise TypeError(
                "the provided class does have a deserialize attribute, but it is not a function"
            )
        if check_annotations:
            ser_signature = inspect.signature(serialization_func)
            if not any(
                param
                for param in ser_signature.parameters.values()
                if param.kind == param.VAR_KEYWORD
            ):
                raise TypeError(
                    "The provided class has a serialization function but does not accept a dict "
                    "of keyword arguments that aren't bound to any other parameter, "
                    "i.e. a '**kwargs' parameter. This is required in the function definition. "
                    "These keyword arguments should also be forwarded to the next serialization "
                    "call."
                )
            deser_signature = inspect.signature(deserialization_func)
            if deser_signature.return_annotation not in (obj_class.__name__, obj_class):
                raise AnnotationError(
                    f"The provided class has a deserialization function, but it does not return "
                    f"an object of type {obj_class_name}. Make sure the function has type "
                    f"annotation '{obj_class_name}' or set check_annotations to False if this is "
                    f"intentional behaviour."
                )
            if not any(
                param
                for param in deser_signature.parameters.values()
                if param.kind == param.VAR_KEYWORD
            ):
                raise TypeError(
                    "The provided class has a deserialization function but does not accept a dict "
                    "of keyword arguments that aren't bound to any other parameter, "
                    "i.e. a '**kwargs' parameter. This is required in the function definition. "
                    "These keyword arguments should also be forwarded to the next deserialization "
                    "call."
                )
            try:
                deser_signature.parameters["obj"]
            except KeyError as exception:
                raise TypeError(
                    "'obj' parameter missing in deserialization function."
                ) from exception
            if (
                ser_signature.return_annotation
                != deser_signature.parameters["obj"].annotation
            ):
                raise AnnotationError(
                    f"Return type of serialization function ({ser_signature.return_annotation}) "
                    f"does not match type of 'obj' parameter in deserialization function "
                    f"({deser_signature.parameters['obj'].annotation})."
                )

        # The object contains valid serialization logic, so we save it for later
        Serialization.custom_serialization_funcs[obj_class_name] = serialization_func
        Serialization.custom_deserialization_funcs[
            obj_class_name
        ] = deserialization_func

    @staticmethod
    def serialize(
        obj: Any,
        use_pickle: bool,
        **kwargs: Any,
    ) -> Union[bytes, Dict[str, bytes]]:
        r"""
        Function that detects with serialization function should be used and applies it

        :param obj: object to serialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback serializer
        :param \**kwargs: optional extra keyword arguments
        :return: serialized object
        """

        obj_class = obj.__class__
        obj_class_name = obj_class.__name__

        # Take the default serialization function
        serialization_func: Callable[
            ..., Any
        ] = lambda _, **l_kwargs: Serialization.default_serialize(
            _, use_pickle, **kwargs
        )

        # Check if there is a specified serialization function in this class
        serialization_func = SERIALIZATION_FUNCS.get(obj_class_name, serialization_func)

        # check if the serialization logic for the object has been added in an earlier stage
        serialization_func = Serialization.custom_serialization_funcs.get(
            obj_class_name, serialization_func
        )
        try:
            data = serialization_func(obj, **kwargs)
        except Exception:
            logger.exception("Serialization failed!")
            raise
        ser_obj = {"type": obj_class_name, "data": data}
        return ser_obj

    # endregion

    @staticmethod
    def pack(
        obj: Any,
        msg_id: Union[str, int],
        use_pickle: bool,
        option: Optional[int] = DEFAULT_PACK_OPTION,
        **kwargs: Any,
    ) -> bytes:
        r"""
        Function that adds metadata and serializes the object for transmission.

        :param obj: object to pack
        :param msg_id: message identifier associated to the message
        :param use_pickle: set to true if one wishes to use pickle as a fallback packer
        :param option: ormsgpack options can be specified through this parameter
        :param \**kwargs: optional extra keyword arguments
        :return: packed object (serialized and annotated)
        """
        dict_object = {"object": obj, "id": msg_id}
        try:
            packed_object = ormsgpack.packb(
                dict_object,
                default=lambda _: Serialization.serialize(_, use_pickle, **kwargs),
                option=option,
            )
        except TypeError:
            logger.exception(
                "Packing failed, consider 1) enabling use_pickle for"
                " inefficient/slow fallback to pickle, or 2) implement"
                " a serialization method for this type/structure, or 3)"
                " resolve the error by setting an option (if available)."
            )
            raise
        return packed_object

    @staticmethod
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
        result: npt.NDArray[np.object_] = np.empty(obj["shape"], dtype=object)
        if obj["values"]:
            result[:] = Serialization.collection_deserialize(obj["values"], **kwargs)
        return result

    @staticmethod
    def tuple_deserialize(obj: List[Any], **kwargs: Any) -> Tuple[Any, ...]:
        r"""
        Function for deserializing tuples

        :param obj: object to deserialize
        :param \**kwargs: optional extra keyword arguments
        :return: deserialized tuple object
        """
        return tuple(Serialization.collection_deserialize(obj, **kwargs))

    @staticmethod
    def int_deserialize(obj: bytes, **_kwargs: Any) -> int:
        r"""
        Function for deserializing Python ints

        :param obj: object to deserialize
        :param \**_kwargs: optional extra keyword arguments
        :return: deserialized int object
        """
        return int.from_bytes(obj, "little", signed=True)

    @staticmethod
    def bitarray_deserialize(obj: bytes, **_kwargs: Any) -> bitarray.bitarray:
        r"""
        Function for deserializing bitarrays

        :param obj: object to deserialize
        :param \**_kwargs: optional extra keyword arguments
        :return: deserialized bitarray object
        """
        return bitarray.util.deserialize(obj)

    @staticmethod
    @typeguard_ignore
    def gmpy_deserialize(obj: bytes, **_kwargs: Any) -> GmpyTypes:
        r"""
        Function for deserializing gmpy objects

        :param obj: object to deserialize
        :param \**_kwargs: optional extra keyword arguments
        :return: deserialized gmpy object
        """
        return gmpy2.from_binary(obj)

    @staticmethod
    def default_deserialize(
        obj: bytes, use_pickle: bool = False, **_kwargs: Any
    ) -> Any:
        r"""
        Fall-back function is case no specific deserialization function is available.
        This function uses the pickle library

        :param obj: object to deserialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback deserializer
        :param \**_kwargs: optional extra keyword arguments
        :return: deserialized object
        """
        if use_pickle:
            return pickle.loads(obj)
        # else
        raise NotImplementedError(
            f"There is no deserialization function defined for "
            f"{obj.__class__.__name__} objects."
        )

    @staticmethod
    def collection_deserialize(
        collection_obj: Union[List[Any], Dict[str, Any]],
        **kwargs: Any,
    ) -> Union[Dict[str, Any], List[Any]]:
        r"""
        Function for deserializing collections

        :param collection_obj: object to deserialize
        :param \**kwargs: optional extra keyword arguments
        :raise ValueError: raised when (nested) value cannot be deserialized
        :return: deserialized collection
        """
        if isinstance(collection_obj, list):
            result_list: List[Any] = []
            for sub_obj in collection_obj:
                deserialized_element = Serialization.deserialize(sub_obj, **kwargs)
                result_list.append(deserialized_element)
            return result_list
        if (
            isinstance(collection_obj, dict)
            and "type" in collection_obj
            and "data" in collection_obj
        ):
            result_dict = {"type": collection_obj["type"], "data": {}}
            for key, value in collection_obj["data"].items():
                result_dict["data"][key] = Serialization.deserialize(value, **kwargs)
            return result_dict
        if isinstance(collection_obj, dict):
            result_dict = {}
            for key, value in collection_obj.items():
                result_dict[key] = Serialization.deserialize(value, **kwargs)
            return result_dict

        raise ValueError("Cannot process collection")

    @staticmethod
    def deserialize(obj: Any, use_pickle: bool = False, **kwargs: Any) -> Any:
        r"""
        Function that detects which deserialization function should be run and calls it

        :param obj: object to deserialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback deserializer
        :param \**kwargs: optional extra keyword arguments
        :return: deserialized object
        """
        if isinstance(obj, list):
            return Serialization.collection_deserialize(
                obj, use_pickle=use_pickle, **kwargs
            )
        if isinstance(obj, dict) and "type" in obj.keys() and "data" in obj.keys():
            if isinstance(obj["data"], dict):
                obj = Serialization.collection_deserialize(
                    obj, use_pickle=use_pickle, **kwargs
                )
            if obj["type"] in Serialization.custom_deserialization_funcs:
                deserialization_func = Serialization.custom_deserialization_funcs[
                    obj["type"]
                ]
            elif obj["type"] in DESERIALIZATION_FUNCS:
                deserialization_func = DESERIALIZATION_FUNCS[obj["type"]]
            else:
                deserialization_func = Serialization.default_deserialize
            return deserialization_func(obj["data"], use_pickle=use_pickle, **kwargs)
        if isinstance(obj, dict):
            return Serialization.collection_deserialize(
                obj, use_pickle=use_pickle, **kwargs
            )
        return obj

    # endregion

    @staticmethod
    def unpack(
        obj: bytes,
        use_pickle: bool = False,
        option: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Any]:
        r"""
        Function that handles metadata and turns the bytes object into a python object

        :param obj: bytes object to unpack
        :param use_pickle: set to true if one wishes to use pickle as a fallback deserializer
        :param option: ormsgpack options can be specified through this parameter
        :param \**kwargs: optional extra keyword arguments
        :return: unpacked object
        """
        try:
            dict_obj = ormsgpack.unpackb(obj, option=option)
        except TypeError:
            logger.exception(
                "Unpacking failed, consider 1) enabling use_pickle for"
                " inefficient/slow fallback to pickle, or 2) implement"
                " a serialization method for this type/structure, or 3)"
                " resolve the error by setting an option (if available)."
            )
            raise
        deserialized_object = Serialization.deserialize(
            dict_obj["object"], use_pickle=use_pickle, **kwargs
        )
        return dict_obj["id"], deserialized_object


DESERIALIZATION_FUNCS: Dict[str, Callable[[Arg(Any, "obj"), KwArg(Any)], Any]] = {
    "int": Serialization.int_deserialize,
    "tuple": Serialization.tuple_deserialize,
}

SERIALIZATION_FUNCS: Dict[str, Callable[[Arg(Any, "obj"), KwArg(Any)], Any]] = {
    "int": Serialization.int_serialize,
    "tuple": Serialization.tuple_serialize,
}

if USE_NUMPY:
    DESERIALIZATION_FUNCS = {
        **DESERIALIZATION_FUNCS,
        **{
            "ndarray": Serialization.numpy_deserialize,
        },
    }
    SERIALIZATION_FUNCS = {
        **SERIALIZATION_FUNCS,
        **{
            "ndarray": Serialization.numpy_serialize,
        },
    }
if USE_BITARRAY:
    DESERIALIZATION_FUNCS = {
        **DESERIALIZATION_FUNCS,
        **{
            "bitarray": Serialization.bitarray_deserialize,
        },
    }
    SERIALIZATION_FUNCS = {
        **SERIALIZATION_FUNCS,
        **{
            "bitarray": Serialization.bitarray_serialize,
        },
    }
if USE_GMPY2:
    DESERIALIZATION_FUNCS = {
        **DESERIALIZATION_FUNCS,
        **{
            "xmpz": Serialization.gmpy_deserialize,
            "mpz": Serialization.gmpy_deserialize,
            "mpfr": Serialization.gmpy_deserialize,
            "mpq": Serialization.gmpy_deserialize,
            "mpc": Serialization.gmpy_deserialize,
        },
    }
    SERIALIZATION_FUNCS = {
        **SERIALIZATION_FUNCS,
        **{
            "xmpz": Serialization.gmpy_serialize,
            "mpz": Serialization.gmpy_serialize,
            "mpfr": Serialization.gmpy_serialize,
            "mpq": Serialization.gmpy_serialize,
            "mpc": Serialization.gmpy_serialize,
        },
    }


class AnnotationError(Exception):
    """
    Raised when an improperly function is incorrectly annotated
    """


class RepetitionError(Exception):
    """
    Raised when the action has already been performed and should not be repeated
    """
