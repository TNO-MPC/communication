"""
This module contains the serialization logic used in sending and receiving arbitrary objects.
"""

from __future__ import annotations

import inspect
import logging
import pickle
import sys
import warnings
from collections.abc import Collection, Container, Iterable
from dataclasses import dataclass, field
from importlib import import_module
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Protocol, TypeVar, Union

import ormsgpack

from tno.mpc.communication import serializer_plugins
from tno.mpc.communication.exceptions import (
    AnnotationError,
    NumpySerializationWarning,
    RepetitionError,
)

logger = logging.getLogger(__name__)

DEFAULT_PACK_OPTION: int | None = (
    ormsgpack.OPT_PASSTHROUGH_BIG_INT
    | ormsgpack.OPT_PASSTHROUGH_TUPLE
    | ormsgpack.OPT_PASSTHROUGH_DATACLASS
    | ormsgpack.OPT_SERIALIZE_NUMPY
)
DEFAULT_UNPACK_OPTION: int | None = None

PICKLE_WARNING = """
Falling back to (de)serialization with pickle. Please be aware that this is a potential security
 risk. If this behaviour is unexpected, please file an issue at the tno.mpc.communication
 repository and elaborate on the exact data object that you try to (de)serialize. If you try to
 (de)serialize a custom object, please refer to the documentation on how to write and register your
 custom (de)serialization logic.
""".replace(
    "\n", ""
)


@dataclass(frozen=True)
class _Opts:
    """
    Options to change the behaviour of serialization and deserialization.
    """

    fallback_pickle: bool = field(default=False)
    """
    Whether to fall back to pickle when no serialization is configured for a type.
    """


@dataclass(frozen=True)
class SerializerOpts(_Opts):
    """
    Options to change the behaviour of serialization.
    """

    ormsgpack_option: int | None = field(default=DEFAULT_PACK_OPTION)
    """
    Option passed to ormsgpack.packb.
    """


@dataclass(frozen=True)
class DeserializerOpts(_Opts):
    """
    Options to change the behaviour of deserialization.
    """

    ormsgpack_option: int | None = field(default=DEFAULT_UNPACK_OPTION)
    """
    Option passed to ormsgpack.unpackb.
    """


DefaultSerializerOpts = SerializerOpts()
DefaultDeserializerOpts = DeserializerOpts()


if TYPE_CHECKING:
    from mypy_extensions import Arg

    SerializerFunction = Union[
        Callable[[Arg(Any, "self"), Arg(SerializerOpts, "opts")], Any],
        Callable[[Arg(Any, "obj"), Arg(SerializerOpts, "opts")], Any],
    ]
    DeserializerFunction = Union[
        Callable[[Arg(Any, "self"), Arg(DeserializerOpts, "opts")], Any],
        Callable[[Arg(Any, "obj"), Arg(DeserializerOpts, "opts")], Any],
    ]
    DorSFunction = TypeVar(
        "DorSFunction", bound=Union[SerializerFunction, DeserializerFunction]
    )


class SupportsSerialization(Protocol):
    """
    Type placeholder for classes supporting custom serialization.
    """

    def serialize(
        self,
        opts: SerializerOpts,
    ) -> Any:
        """
        Serialize this object into bytes.

        :param opts: Options to change the behaviour of the serialization.
        :return: Serialization of this instance to Dict with bytes.
        """

    @staticmethod
    def deserialize(obj: Any, opts: DeserializerOpts) -> SupportsSerialization:
        """
        Deserialize the given object into an object of this class.

        :param obj: Object to be deserialized.
        :param opts: Options to change the behaviour of the deserialization.
        :return: Deserialized object.
        """


class Serializer:
    """
    Virtual class that provides packing and unpacking functions used for communications.
    The outline is as follows:
    - serialization functions for different classes
    - packing function that handles metadata and determines which serialization needs to happen

    - deserialization functions for different classes
    - unpacking function that handles metadata and determines which deserialization needs to happen
    """

    _serializer_funcs: ClassVar[
        dict[
            str,
            SerializerFunction,
        ]
    ] = {}
    _deserializer_funcs: ClassVar[
        dict[
            str,
            DeserializerFunction,
        ]
    ] = {}

    @classmethod
    def register_class(
        cls,
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
        cls.register(
            serialization_func,
            deserialization_func,
            obj_class_name,
            check_annotations=check_annotations,
            overwrite=overwrite,
        )

    @classmethod
    def register(
        cls,
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
        cls._register_serializer(
            serializer,
            types,
            check_annotations=check_annotations,
            overwrite=overwrite,
        )
        cls._register_deserializer(
            deserializer,
            types,
            check_annotations=check_annotations,
            overwrite=overwrite,
        )

    @classmethod
    def clear_serialization_logic(cls, reload_defaults: bool = True) -> None:
        """
        Clear all custom serialization (and deserialization) logic that was added to this class.

        :param reload_defaults: After clearing, reload the (de)serialization logic that is
            provided by the package.
        """
        cls._serializer_funcs.clear()
        cls._deserializer_funcs.clear()
        if reload_defaults:
            serializer_plugins.register_defaults()

    @classmethod
    def serialize(
        cls,
        obj: Any,
        opts: SerializerOpts = DefaultSerializerOpts,
    ) -> bytes:
        """
        Function that serializes the object for transmission.

        :param obj: Object to pack.
        :param opts: Options to change the behaviour of the serialization
        :raise TypeError: Failed to serialize the provided object.
        :return: Packed object (serialized and annotated).
        """
        try:
            import numpy as np  # pylint: disable=import-outside-toplevel
        except ImportError:
            pass

        if "numpy" in sys.modules and isinstance(obj, np.ndarray):
            warnings.warn(
                (
                    "Due to limitations with the underlying serialization library (ormsgpack), "
                    "numpy arrays may be deserialized as nested lists. To avoid surprises, we "
                    "suggest to run np.asarray on the deserialized object."
                ),
                NumpySerializationWarning,
            )

        try:
            packed_object = ormsgpack.packb(
                obj,
                default=lambda _: cls.transform_into_native(_, opts),
                option=(
                    opts.ormsgpack_option if opts else SerializerOpts.ormsgpack_option
                ),
            )
        except TypeError:
            logger.exception(
                "Packing failed, consider 1) enabling fallback_pickle for"
                " inefficient/slow fallback to pickle, or 2) implement"
                " a serialization method for this type/structure, or 3)"
                " resolve the error by setting an option (if available)."
            )
            raise
        return packed_object

    @classmethod
    def deserialize(
        cls,
        obj: bytes,
        opts: DeserializerOpts = DefaultDeserializerOpts,
    ) -> Any:
        """
        Function that turns the bytes object into a python object

        :param obj: Bytes object to unpack.
        :param opts: Options to change the behaviour of the serialization.
        :raise TypeError: Failed to deserialize the provided object
        :return: Unpacked object.
        """
        try:
            dict_obj = ormsgpack.unpackb(
                obj,
                option=(
                    opts.ormsgpack_option if opts else DeserializerOpts.ormsgpack_option
                ),
            )
        except TypeError:
            logger.exception(
                "Unpacking failed, consider 1) enabling fallback_pickle for"
                " inefficient/slow fallback to pickle, or 2) implement"
                " a serialization method for this type/structure, or 3)"
                " resolve the error by setting an option (if available)."
            )
            raise
        deserialized_object = cls.transform_into_nonnative(dict_obj, opts)
        return deserialized_object

    @classmethod
    def _register_serializer(
        cls,
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
            signature = _get_signature(serializer)
            # For all deserializers registered to the given types, verify that serializer is
            # compatible with their signatures.
            same_type_deserializers = (
                d for t, d in cls._deserializer_funcs.items() if t in types
            )
            for des in same_type_deserializers:
                _validate_signatures_consistent(
                    serializer_signature=signature,
                    deserializer_signature=_get_signature(des),
                )

        _register(cls._serializer_funcs, serializer, types, overwrite=overwrite)

    @classmethod
    def _register_deserializer(
        cls,
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
            signature = _get_signature(deserializer)
            _validate_provided_return_annotation(signature, types)
            _validate_signature_accepts_keyword(signature, "obj")
            # For all serializers registered to the given types, verify that deserializer is
            # compatible with their signatures.
            same_type_serializers = (
                s for t, s in cls._serializer_funcs.items() if t in types
            )
            for ser in same_type_serializers:
                _validate_signatures_consistent(
                    serializer_signature=_get_signature(ser),
                    deserializer_signature=signature,
                )

        _register(cls._deserializer_funcs, deserializer, types, overwrite=overwrite)

    @classmethod
    def transform_into_native(
        cls,
        obj: Any,
        opts: SerializerOpts,
    ) -> bytes | dict[str, bytes]:
        r"""
        Given an object with non-native types (that is: not supported by ormsgpack), this function
        transforms the non-native types into native types. For example, the ormsgpack does not
        serialize tuples so we transform them into dictionaries and lists.

        >>> Serializer.transform_into_native((1, 2, 3))
        {"type": "tuple", "data": [1, 2, 3]}

        This function is usually called by serializer plugins to transform (nested,) non-native
        objects into native types.

        :param obj: Object to transform.
        :param opts: Options to change the behaviour of the serialization.
        :raise Exception: Raised when object cannot be serialized.
        :return: Transformed object.
        """
        obj_class_name = obj.__class__.__name__

        # check if the serialization logic for the object has been added in an earlier stage
        serialization_func: SerializerFunction = cls._serializer_funcs.get(
            obj_class_name, _default_serialize
        )

        try:
            data = serialization_func(obj, opts)
        except Exception:
            logger.exception("Serialization failed!")
            raise
        ser_obj = {"type": obj_class_name, "data": data}
        return ser_obj

    @classmethod
    def transform_into_nonnative(
        cls,
        obj: Any,
        opts: DeserializerOpts,
    ) -> Any:
        r"""
        Given an object that is deserialized into native types (that is: supported by ormsgpack),
        this function transforms the native types back into non-native types in a depth-first
        manner. For example, the ormsgpack does not serialize tuples so we conjugate them from
        dictionaries and lists.

        >>> Serializer.transform_into_nonnative({"numbers": {"type": "tuple", "data": [1, 2, 3]}, "myname": "beth"})
        {"numbers": (1, 2, 3), "myname": "beth"}

        This function is usually called by serializer plugins to transform nested objects back into
        their expected, non-native types.

        :param obj: object to transform
        :param opts: options to change the behaviour of the serialization
        :return: transformed object
        """
        if isinstance(obj, list):
            return cls._transform_collection_into_nonnative(obj, opts)
        if isinstance(obj, dict) and "type" in obj.keys() and "data" in obj.keys():
            if isinstance(obj["data"], dict):
                obj = cls._transform_collection_into_nonnative(obj, opts)

            deserialization_func: DeserializerFunction = cls._deserializer_funcs.get(
                obj["type"], _default_deserialize
            )
            return deserialization_func(obj["data"], opts)
        if isinstance(obj, dict):
            return cls._transform_collection_into_nonnative(obj, opts)
        return obj

    @classmethod
    def _transform_collection_into_nonnative(
        cls,
        collection_obj: list[Any] | dict[str, Any],
        opts: DeserializerOpts,
    ) -> dict[str, Any] | list[Any]:
        """
        Function for deserializing collections

        :param collection_obj: object to deserialize
        :param opts: options to change the behaviour of the serialization
        :raise ValueError: raised when (nested) value cannot be deserialized
        :return: deserialized collection
        """
        if isinstance(collection_obj, list):
            result_list: list[Any] = []
            for sub_obj in collection_obj:
                deserialized_element = cls.transform_into_nonnative(sub_obj, opts)
                result_list.append(deserialized_element)
            return result_list
        if (
            isinstance(collection_obj, dict)
            and "type" in collection_obj
            and "data" in collection_obj
        ):
            result_dict = {"type": collection_obj["type"], "data": {}}
            for key, value in collection_obj["data"].items():
                result_dict["data"][key] = cls.transform_into_nonnative(value, opts)
            return result_dict
        if isinstance(collection_obj, dict):
            result_dict = {}
            for key, value in collection_obj.items():
                result_dict[key] = cls.transform_into_nonnative(value, opts)
            return result_dict

        raise ValueError("Cannot process collection")


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
            raise RepetitionError(f"The logic for type {type_} has already been set")
        target_dict[type_] = d_or_s_function


def _default_serialize(
    obj: Any,
    opts: SerializerOpts,
) -> bytes:
    """
    Fall-back function is case no specific serialization function is available.
    This function uses the pickle library

    :param obj: object to serialize
    :param opts: options to change the behaviour of the serialization
    :raise NotImplementedError: raised when no serialization function is defined for object
    :return: serialized object
    """
    if opts and opts.fallback_pickle:
        warnings.warn(PICKLE_WARNING)
        return pickle.dumps(obj)
    # else
    raise NotImplementedError(
        f"""There is no serialization function defined for
        {obj.__class__.__name__} objects.

        If you created a class that you wish to send via the communication
        module, you need to add and implement the methods `serialize` and
        `deserialize` and register your class:
        `Serialization.register_class(YourClass)`.
        """
    )


def _default_deserialize(
    obj: bytes,
    opts: DeserializerOpts,
) -> Any:
    """
    Fall-back function is case no specific deserialization function is available.
    This function uses the pickle library

    :param obj: object to deserialize
    :param opts: options to change the behaviour of the serialization
    :raise NotImplementedError: Default serialization not possible for the provided object and
        arguments
    :return: deserialized object
    """
    if opts and opts.fallback_pickle:
        warnings.warn(PICKLE_WARNING)
        return pickle.loads(obj)
    # else
    raise NotImplementedError(
        f"""There is no deserialization function defined for
        {obj.__class__.__name__} objects.

        If you created a class that you wish to send via the communication
        module, you need to add and implement the methods `serialize` and
        `deserialize` and register your class:
        `Serialization.register_class(YourClass)`.

        If the class you are sending/receiving is not your custom class, it
        could be that you forgot to import it.

        Note: When a Client in a Pool *receives* an object, it also *must*
        import the type it receives, in order to have its deserialization
        function registered.

        E.g. When you send a PaillierCiphertext from Alice to Bob, Bob
        *must* import the PaillierCiphertext in order to have its
        deserialization function registered.
        """
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
        and getattr(signature.return_annotation, "__name__", None) not in types
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


def _get_signature(obj: Any) -> inspect.Signature:
    """
    Get the object signature.

    :param obj: Object to get signature from.
    :return: Signature.
    """
    try:
        if sys.version_info >= (3, 10):
            return inspect.signature(obj, eval_str=True)
        else:
            s = inspect.signature(obj)
            r = s.return_annotation
            if isinstance(r, str):
                r_mod, r_obj = r.split(".", 1)
                r_mod_alias = import_module(r_mod)
                s = s.replace(return_annotation=getattr(r_mod_alias, r_obj))
            return s
    except Exception:
        return inspect.signature(obj)
