"""
This module contains the serialization logic used in sending and receiving arbitrary objects.
"""

from __future__ import annotations

import inspect
import pickle
from functools import partial
from typing import (
    Any,
    Callable,
    Collection,
    Container,
    Iterable,
    Protocol,
    TypeVar,
    Union,
)

import ormsgpack
from mypy_extensions import Arg, KwArg

from tno.mpc.communication import serializer_plugins
from tno.mpc.communication.exceptions import AnnotationError, RepetitionError
from tno.mpc.communication.functions import init

logger = init(__name__)

SerializerFunction = Union[
    Callable[[Arg(Any, "self"), KwArg(Any)], Any],
    Callable[[Arg(Any, "obj"), KwArg(Any)], Any],
    Callable[[Arg(Any, "self"), Arg(bool, "use_pickle"), KwArg(Any)], Any],
    Callable[[Arg(Any, "obj"), Arg(bool, "use_pickle"), KwArg(Any)], Any],
]
DeserializerFunction = Union[
    Callable[[Arg(Any, "obj"), KwArg(Any)], Any],
    Callable[[Arg(Any, "obj"), Arg(bool, "use_pickle"), KwArg(Any)], Any],
]
DorSFunction = TypeVar(
    "DorSFunction", bound=Union[SerializerFunction, DeserializerFunction]
)

DEFAULT_PACK_OPTION = (
    ormsgpack.OPT_PASSTHROUGH_BIG_INT
    | ormsgpack.OPT_PASSTHROUGH_TUPLE
    | ormsgpack.OPT_PASSTHROUGH_DATACLASS
    | ormsgpack.OPT_SERIALIZE_NUMPY
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


SERIALIZER_FUNCS: dict[
    str,
    SerializerFunction,
] = {}
DESERIALIZER_FUNCS: dict[
    str,
    DeserializerFunction,
] = {}


class Serialization:
    """
    Virtual class that provides packing and unpacking functions used for communications.
    The outline is as follows:
    - serialization functions for different classes
    - packing function that handles metadata and determines which serialization needs to happen

    - deserialization functions for different classes
    - unpacking function that handles metadata and determines which deserialization needs to happen
    """

    @staticmethod
    def register_class(
        obj_class: type[SupportsSerialization],
        check_annotations: bool = True,
        overwrite: bool = False,
    ) -> None:
        """
        Register (de)serialization logic associated to SupportsSerialization objects.

        :param obj_class: object class to set serialization logic for.
        :param check_annotations: validate return annotation of the serialization logic.
        :param overwrite: Allow (silent) overwrite of currently registered serializers.
        :raise RepetitionError: raised when serialization function is already defined for object class.
        :raise TypeError: raised when provided object class has no (de)serialization function.
        :raise AnnotationError: raised when the return annotation is inconsistent.
        """
        obj_class_name = obj_class.__name__
        serialization_func: SerializerFunction = obj_class.serialize
        deserialization_func: DeserializerFunction = obj_class.deserialize
        Serialization.register(
            serialization_func,
            deserialization_func,
            obj_class_name,
            check_annotations=check_annotations,
            overwrite=overwrite,
        )

    @staticmethod
    def register(
        serializer: SerializerFunction,
        deserializer: DeserializerFunction,
        *types: str,
        check_annotations: bool = True,
        overwrite: bool = False,
    ) -> None:
        """
        Register serialization and deserialization functions.

        :param serializer: Serializer function.
        :param deserializer: Deserializer function.
        :param types: Object types that the serializer can serialize.
        :param check_annotations: Verify annotations of the (de)serializer conform to the protocol.
        :param overwrite: Allow (silent) overwrite of currently registered serializers.
        :raise RepetitionError: Attempted overwrite of registered serialization function.
        :raise TypeError: Annotations do not conform to the protocol.
        """
        Serialization._register_serializer(
            serializer,
            types,
            check_annotations=check_annotations,
            overwrite=overwrite,
        )
        Serialization._register_deserializer(
            deserializer,
            types,
            check_annotations=check_annotations,
            overwrite=overwrite,
        )

    @staticmethod
    def _register_serializer(
        serializer: SerializerFunction,
        types: Collection[str],
        check_annotations: bool = True,
        overwrite: bool = False,
    ) -> None:
        """
        Register a serializer function.

        :param serializer: Serializer function.
        :param types: Object types that the serializer can serialize.
        :param check_annotations: Verify annotations of the serializer conform to the protocol.
        :param overwrite: Allow (silent) overwrite of currently registered serializers.
        :raise RepetitionError: Attempted overwrite of registered serialization function.
        :raise TypeError: Annotations do not conform to the protocol.
        """
        if not callable(serializer):
            raise TypeError("The provided serializer is not a function.")
        if check_annotations:
            signature = inspect.signature(serializer)
            _validate_signature_has_kwargs(signature)
            # For all deserializers registered to the given types, verify that serializer is
            # compatible with their signatures.
            same_type_deserializers = (
                d for t, d in DESERIALIZER_FUNCS.items() if t in types
            )
            for des in same_type_deserializers:
                _validate_signatures_consistent(
                    serializer_signature=signature,
                    deserializer_signature=inspect.signature(des),
                )

        Serialization._register(
            SERIALIZER_FUNCS, serializer, types, overwrite=overwrite
        )

    @staticmethod
    def _register_deserializer(
        deserializer: DeserializerFunction,
        types: Collection[str],
        check_annotations: bool = True,
        overwrite: bool = False,
    ) -> None:
        """
        Register a deserializer function.

        :param deserializer: Deserializer function.
        :param types: Object types that the serializer can serialize.
        :param check_annotations: Verify annotations of the deserializer conform to the protocol.
        :param overwrite: Allow (silent) overwrite of currently registered serializers.
        :raise RepetitionError: Attempted overwrite of registered serialization function.
        :raise TypeError: Annotations do not conform to the protocol.
        """
        if not callable(deserializer):
            raise TypeError("The provided deserializer is not a function.")
        if check_annotations:
            signature = inspect.signature(deserializer)
            _validate_signature_has_kwargs(signature)
            _validate_provided_return_annotation(signature, types)
            _validate_signature_accepts_keyword(signature, "obj")
            # For all serializers registered to the given types, verify that deserializer is
            # compatible with their signatures.
            same_type_serializers = (
                s for t, s in SERIALIZER_FUNCS.items() if t in types
            )
            for ser in same_type_serializers:
                _validate_signatures_consistent(
                    serializer_signature=inspect.signature(ser),
                    deserializer_signature=signature,
                )

        Serialization._register(
            DESERIALIZER_FUNCS, deserializer, types, overwrite=overwrite
        )

    @staticmethod
    def _register(
        target_dict: dict[str, DorSFunction],
        d_or_s_function: DorSFunction,
        types: Iterable[str],
        overwrite: bool,
    ) -> None:
        """
        In-place add (de)serializer to a target dictionary for multiple keys.

        :param target_dict: Target dictionary.
        :param d_or_s_function: (De)serializer to register in the target dictionary
        :param types: Types of objects that the provided (de)serializer can be applied to.
        :param overwrite: Allow (silent) overwrite of currently registered serializers.
        :raise RepetitionError: Attempted overwrite of registered (de)serializer.
        """
        for type_ in types:
            if type_ in target_dict and not overwrite:
                raise RepetitionError(
                    f"The logic for type {type_} has already been set"
                )
            target_dict[type_] = d_or_s_function

    @staticmethod
    def clear_serialization_logic(reload_defaults: bool = True) -> None:
        """
        Clear all custom serialization (and deserialization) logic that was added to this class.

        :param reload_defaults: After clearing, reload the (de)serialization logic that is
            provided by the package.
        """
        SERIALIZER_FUNCS.clear()
        DESERIALIZER_FUNCS.clear()
        if reload_defaults:
            serializer_plugins.register_defaults()

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
    def serialize(
        obj: Any,
        use_pickle: bool,
        **kwargs: Any,
    ) -> bytes | dict[str, bytes]:
        r"""
        Function that detects with serialization function should be used and applies it

        :param obj: object to serialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback serializer
        :param \**kwargs: optional extra keyword arguments
        :return: serialized object
        """
        # pylint: disable=missing-raises-doc

        obj_class = obj.__class__
        obj_class_name = obj_class.__name__

        # Take the default serialization function
        default_serializer: SerializerFunction = partial(
            Serialization.default_serialize, use_pickle=use_pickle
        )

        # check if the serialization logic for the object has been added in an earlier stage
        serialization_func = SERIALIZER_FUNCS.get(obj_class_name, default_serializer)

        try:
            data = serialization_func(obj, use_pickle=use_pickle, **kwargs)
        except Exception:
            logger.exception("Serialization failed!")
            raise
        ser_obj = {"type": obj_class_name, "data": data}
        return ser_obj

    @staticmethod
    def pack(
        obj: Any,
        msg_id: str | int,
        use_pickle: bool,
        option: int | None = DEFAULT_PACK_OPTION,
        **kwargs: Any,
    ) -> bytes:
        r"""
        Function that adds metadata and serializes the object for transmission.

        :param obj: object to pack
        :param msg_id: message identifier associated to the message
        :param use_pickle: set to true if one wishes to use pickle as a fallback packer
        :param option: ormsgpack options can be specified through this parameter
        :param \**kwargs: optional extra keyword arguments
        :raise TypeError: Failed to serialize the provided object
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
    def default_deserialize(
        obj: bytes, use_pickle: bool = False, **_kwargs: Any
    ) -> Any:
        r"""
        Fall-back function is case no specific deserialization function is available.
        This function uses the pickle library

        :param obj: object to deserialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback deserializer
        :param \**_kwargs: optional extra keyword arguments
        :raise NotImplementedError: Default serialization not possible for the provided object and
            arguments
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
        collection_obj: list[Any] | dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        r"""
        Function for deserializing collections

        :param collection_obj: object to deserialize
        :param \**kwargs: optional extra keyword arguments
        :raise ValueError: raised when (nested) value cannot be deserialized
        :return: deserialized collection
        """
        if isinstance(collection_obj, list):
            result_list: list[Any] = []
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

            default_deserializer: DeserializerFunction = partial(
                Serialization.default_deserialize, use_pickle=use_pickle
            )
            deserialization_func = DESERIALIZER_FUNCS.get(
                obj["type"], default_deserializer
            )
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
        option: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, Any]:
        r"""
        Function that handles metadata and turns the bytes object into a python object

        :param obj: bytes object to unpack
        :param use_pickle: set to true if one wishes to use pickle as a fallback deserializer
        :param option: ormsgpack options can be specified through this parameter
        :param \**kwargs: optional extra keyword arguments
        :raise TypeError: Failed to deserialize the provided object
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


def _validate_signature_has_kwargs(signature: inspect.Signature) -> None:
    """
    Validate that the provided signature accepts kwargs.

    :param signature: Signature to validate.
    :raise TypeError: Signature does not contain kwargs.
    """
    if not any(
        param
        for param in signature.parameters.values()
        if param.kind == param.VAR_KEYWORD
    ):
        raise TypeError(
            "The provided (de)serializer does not accept a dict of keyword arguments that aren't "
            "bound to any other parameter, i.e. a '**kwargs' parameter. This is required in the "
            "function definition. These keyword arguments should also be forwarded to the next "
            "(de)serialization call."
        )


def _validate_provided_return_annotation(
    signature: inspect.Signature, types: Container[str]
) -> None:
    """
    Validate that the signature agrees with the provided types.

    :param signature: Signature to validate.
    :param types: Types that are supposedly consistent with the signature.
    :raise AnnotationError: Types and signature do not agree.
    """
    if (
        signature.return_annotation not in types
        and signature.return_annotation.__name__ not in types
    ):
        raise AnnotationError(
            f"Expected the provided deserialization function to return objects of type {types}, "
            f"but detected return type annotation for {signature.return_annotation}. Make sure "
            f"the function has type annotation '{types}' or set 'check_annotations' to False if "
            "this is intentional behaviour."
        )


def _validate_signature_accepts_keyword(
    signature: inspect.Signature, word: str
) -> None:
    """
    Validate that the signature has a certain parameter (keyword).

    :param signature: Signature to validate.
    :param word: Keyword to test against.
    :raise TypeError: Signature does not accept keyword.
    """
    try:
        signature.parameters[word]
    except KeyError as exception:
        raise TypeError(
            "The provided (de)serializer is missing the following parameter in its signature: "
            f"{word}."
        ) from exception


def _validate_signatures_consistent(
    serializer_signature: inspect.Signature, deserializer_signature: inspect.Signature
) -> None:
    """
    Validate that annotations of serializer and deserializer are consistent.

    :param serializer_signature: Signature of serializer.
    :param deserializer_signature: Signature of deserializer.
    :raise AnnotationError: Return type of serializer does not agree with expected input type of
        deserializer.
    """
    if (
        serializer_signature.return_annotation
        != deserializer_signature.parameters["obj"].annotation
    ):
        raise AnnotationError(
            f"Return type of serialization function ({serializer_signature.return_annotation}) "
            f"does not match type of 'obj' parameter in deserialization function "
            f"({deserializer_signature.parameters['obj'].annotation})."
        )
