"""
This module contains the serialization logic used in sending and receiving arbitrary objects.
"""

from __future__ import annotations

import base64
import inspect
import json
import pickle
from typing import Any, Callable, ClassVar, Dict, List, Tuple, Type, TypeVar, Union

import numpy as np
from mypy_extensions import Arg, KwArg
from typing_extensions import Protocol


class SupportsSerialization(Protocol):
    """
    Type placeholder for classes supporting custom serialization.
    """

    def serialize(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Serialize this object into a JSON dict.

        :param kwargs: Optional extra keyword arguments.
        :return: Serialization of this instance as a JSON dict.
        """

    @staticmethod
    def deserialize(json_obj: Dict[str, Any], **kwargs: Any) -> SupportsSerialization:
        """
        Deserialize the given JSON dict into an object of this class.

        :param json_obj: JSON dict to be deserialized.
        :param kwargs: Optional extra keyword arguments.
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

    # variable that determines whether pickle is used when an unspecified class is serialized or
    # an error is shown
    default_use_pickle = True
    # Variable that determines whether phe ciphertexts are checked for obfuscation before sending
    # by default
    default_verify_obfuscation = True

    # dictionary for serialization functions of classes that are not specified here
    new_serialization_funcs: ClassVar[
        Dict[
            str,
            Callable[[Arg(SupportsSerialization, "self"), KwArg(Any)], Dict[str, Any]],
        ]
    ] = {}
    # dictionary for deserialization functions of classes that are not specified here
    new_deserialization_funcs: ClassVar[
        Dict[
            str,
            Callable[
                [Arg(Dict[str, Any], "json_obj"), KwArg(Any)], SupportsSerialization
            ],
        ]
    ] = {}

    # region serialization functions

    @staticmethod
    def standard_serialize(obj: StandardT, **_kwargs: Any) -> Dict[str, StandardT]:
        """
        Function for the most basic way of serialization that works for basic data types, such as
        int, float, string

        :param obj: object to serialize
        :param _kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"value": obj}

    @staticmethod
    def bytes_serialize(obj: bytes, **_kwargs: Any) -> Dict[str, str]:
        """
        Function for serializing bytes

        :param obj: bytes object to serialize
        :param _kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"value": str(base64.b64encode(obj), "utf-8")}

    @staticmethod
    def default_serialize(
        obj: Any, use_pickle: bool = default_use_pickle, **kwargs: Any
    ) -> Dict[str, Dict[str, str]]:
        """
        Fall-back function is case no specific serialization function is available.
        This function uses the pickle library

        :param obj: object to serialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback serializer
        :param kwargs: optional extra keyword arguments
        :raise NotImplementedError: raised when no serialization function is defined for object
        :return: serialized object
        """
        if use_pickle:
            return {"dump": Serialization.bytes_serialize(pickle.dumps(obj), **kwargs)}
        # else
        raise NotImplementedError(
            f"There is no serialization function defined for "
            f"{obj.__class__.__name__} objects."
        )

    @staticmethod
    def extract_keys(result: Dict[str, Any], serialized_element: Any) -> None:
        """
        function that unpacks low level results for collection serialization

        :param result: dictionary to store the extracted results in
        :param serialized_element: elements to extract
        """
        for key in serialized_element["keys"]:
            if key in result["keys"]:
                result["keys"][key].extend(serialized_element["keys"][key])
            else:
                result["keys"][key] = serialized_element["keys"][key]

    @staticmethod
    def collection_serialize(
        collection: Union[Dict[Any, Any], List[Any]],
        use_pickle: bool = default_use_pickle,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        function to serialize lists and dictionaries

        The structure of the collection is saved in a class tree, that has the same structure
        as the original collection, but instead of values it contains the class types.
        All 'leaf' values inside the collection are added to a one-dimensional
        list for each key of the serialization of all the leaves

        :param collection: collection to serialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback serializer
        :param kwargs: optional extra keyword arguments
        :return: serialized collection
        """
        result: Dict[str, Any] = {"class_tree": [], "keys": {}}

        # if the collection is a dictionary, recursively serialize the keys as a list and
        # the values as a list  and save them in a tuple marked with a 'dict' tag and
        # extract the class trees
        if isinstance(collection, dict):
            # serialize the keys
            serialized_keys = Serialization.collection_serialize(
                list(collection.keys()), use_pickle, **kwargs
            )
            # serialize the values
            serialized_values = Serialization.collection_serialize(
                list(collection.values()), use_pickle, **kwargs
            )
            # extract the class trees and combine them into a tuple tagged with 'dict'
            result["class_tree"] = (
                "dict",
                serialized_keys["class_tree"],
                serialized_values["class_tree"],
            )
            # for each key in the serialized list, add the values to the appropriate list
            Serialization.extract_keys(result, serialized_keys)
            Serialization.extract_keys(result, serialized_values)

        # if the collection is a list, we recursively serialize each element inside the list
        # and extract the keys and values and the class tree
        elif isinstance(collection, list):
            for element in collection:
                # serialize the element
                serialized_element = Serialization.collection_serialize(
                    element, use_pickle, **kwargs
                )
                # extract the class tree
                element_class_tree = serialized_element["class_tree"]
                # compress a class tree with repeated entries
                if result["class_tree"]:
                    # if the last element is a compressed list
                    is_comp_list = (
                        isinstance(result["class_tree"][-1], tuple)
                        and len(result["class_tree"][-1]) == 2
                    )
                    if is_comp_list:
                        # extract the type and counter
                        tuple_type, count = result["class_tree"][-1]
                        # check if we can add this type to the tuple or need to start a new entry
                        if tuple_type == element_class_tree:
                            result["class_tree"][-1] = (tuple_type, count + 1)
                        else:
                            result["class_tree"].append(element_class_tree)
                    # check if the last element has the same type
                    elif result["class_tree"][-1] == element_class_tree:
                        # combine into a tuple
                        result["class_tree"][-1] = (element_class_tree, 2)
                    else:
                        result["class_tree"].append(element_class_tree)
                else:
                    result["class_tree"].append(element_class_tree)
                # for each key in the serialized list, add the values to the appropriate list
                Serialization.extract_keys(result, serialized_element)

        # if we encounter a 'leaf' inside the collection, apply regular serialization and
        # rename the keys so that they can be found during deserialization and let its class tree
        # be the class type
        else:
            # regular serialization of the element
            serialized_element = Serialization.serialize(
                collection, use_pickle, **kwargs
            )
            element_type = serialized_element["type"]
            processed_data = {}
            # rename the keys
            for key in serialized_element["data"]:
                processed_key = element_type + "_" + key
                processed_data[processed_key] = [serialized_element["data"][key]]

            result["class_tree"] = element_type
            result["keys"] = processed_data
        return result

    @staticmethod
    def clear_new_serialization_logic() -> None:
        """
        Clear all custom serialization (and deserialization) logic that was added to this class.
        """
        Serialization.new_serialization_funcs = {}
        Serialization.new_deserialization_funcs = {}

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
            obj_class_name in Serialization.new_serialization_funcs
            and obj_class_name in Serialization.new_deserialization_funcs
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
            if ser_signature.return_annotation not in (
                dict,
                "dict",
                Dict[str, Any],
                "Dict[str, Any]",
            ):
                raise AnnotationError(
                    "The provided class has a serialization function, but it does not return "
                    "a dictionary. Make sure the function has type annotation 'dict' or set"
                    "check_annotations to False if this is intentional behaviour."
                )
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

        # The object contains valid serialization logic, so we save it for later
        Serialization.new_serialization_funcs[obj_class_name] = serialization_func
        Serialization.new_deserialization_funcs[obj_class_name] = deserialization_func

    @staticmethod
    def serialize(
        obj: Any,
        use_pickle: bool = default_use_pickle,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Function that detects with serialization function should be used and applies it

        :param obj: object to serialize
        :param use_pickle: set to true if one wishes to use pickle as a fallback serializer
        :param kwargs: optional extra keyword arguments
        :return: serialized object
        """
        serialization_funcs: Dict[
            str, Callable[[Arg(Any, "obj"), KwArg(Any)], Dict[str, Any]]
        ] = {
            "int": Serialization.standard_serialize,
            "float": Serialization.standard_serialize,
            "bytes": Serialization.bytes_serialize,
            "str": Serialization.standard_serialize,
            "list": lambda o, **l_kwargs: Serialization.collection_serialize(
                o, use_pickle, **l_kwargs
            ),
            "tuple": lambda t, **l_kwargs: Serialization.collection_serialize(
                list(t), use_pickle, **l_kwargs
            ),
            "ndarray": lambda a, **l_kwargs: Serialization.collection_serialize(
                list(a), use_pickle, **l_kwargs
            ),
            "dict": lambda d, **l_kwargs: Serialization.collection_serialize(
                d, use_pickle, **l_kwargs
            ),
        }

        obj_class = obj.__class__
        obj_class_name = obj_class.__name__

        # Take the default serialization function
        serialization_func: Union[
            Callable[[Arg(Any, "obj"), KwArg(Any)], Dict[str, Any]],
            Callable[[Arg(SupportsSerialization, "self"), KwArg(Any)], Dict[str, Any]],
            Callable[[Arg(Any, "o"), KwArg(Any)], Dict[str, Dict[str, str]]],
        ] = lambda o, **l_kwargs: Serialization.default_serialize(
            o, use_pickle, **l_kwargs
        )

        # check if the serialization logic for the object has been added in an earlier stage
        serialization_func = Serialization.new_serialization_funcs.get(
            obj_class_name, serialization_func
        )

        # Check if there is a specified serialization function in this class
        serialization_func = serialization_funcs.get(obj_class_name, serialization_func)

        ser_obj = {"type": obj_class_name, "data": serialization_func(obj, **kwargs)}
        return ser_obj

    # endregion

    @staticmethod
    def pack(
        obj: Any,
        msg_id: Union[str, int],
        use_pickle: bool = default_use_pickle,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Function that adds metadata and serializes the object for transmission.

        :param obj: object to pack
        :param msg_id: message identifier associated to the message
        :param use_pickle: set to true if one wishes to use pickle as a fallback packer
        :param kwargs: optional extra keyword arguments
        :return: packed object (serialized and annotated)
        """
        json_object = Serialization.serialize(obj, use_pickle, **kwargs)
        json_object["id"] = msg_id
        return json_object

    # region deserialization functions
    @staticmethod
    def standard_deserialize(
        json_obj: Dict[str, StandardT], **_kwargs: Any
    ) -> StandardT:
        """
        Function for the most basic way of deserialization that works for basic data types, such as
        int, float, string

        :param json_obj: object to deserialize
        :param _kwargs: optional extra keyword arguments
        :return: deserialized object
        """
        return json_obj["value"]

    @staticmethod
    def bytes_deserialize(json_obj: Dict[str, str], **_kwargs: Any) -> bytes:
        """
        Function for deserializing bytes

        :param json_obj: object to deserialize
        :param _kwargs: optional extra keyword arguments
        :return: deserialized bytes object
        """
        return base64.b64decode(json_obj["value"])

    @staticmethod
    def list_deserialize(json_obj: Dict[str, Any], **kwargs: Any) -> List[Any]:
        """
        Function for deserializing lists

        :param json_obj: object to deserialize
        :param kwargs: optional extra keyword arguments
        :return: deserialized list object
        """
        if json_obj["same_type"]:
            return Serialization.list_deserialize_same_type(json_obj, **kwargs)
        # else
        return Serialization.list_deserialize_dif_type(json_obj, **kwargs)

    @staticmethod
    def list_deserialize_same_type(
        json_obj: Dict[str, Any], **kwargs: Any
    ) -> List[Any]:
        """
        Function for deserializing a list containing objects of only one type.

        :param json_obj: object to deserialize
        :param kwargs: optional extra keyword arguments
        :return: deserialized list of which the contents have also been deserialized
        """
        element_type = json_obj["inner_type"]
        length = json_obj["len"]
        keys = json_obj["other_keys"].keys()
        reconstructed_list = []
        for i in range(length):
            entry = {"type": element_type, "data": {}}
            for key in keys:
                entry["data"][key] = json_obj["other_keys"][key][i]
            reconstructed_list.append(entry)

        def deserialize(obj: Dict[str, Any]) -> Any:
            """
            Deserialize this object using the outer method's keyword arguments.

            :param obj: Json description of object to be deserialized
            :return: Deserialized object
            """
            return Serialization.deserialize(obj, **kwargs)

        return list(map(deserialize, reconstructed_list))

    @staticmethod
    def list_deserialize_dif_type(json_obj: Dict[str, Any], **kwargs: Any) -> List[Any]:
        """
        Function for deserializing a list containing objects of more than one type.

        :param json_obj: object to deserialize
        :param kwargs: optional extra keyword arguments
        :return: deserialized list of which the contents have also been deserialized
        """

        def deserialize(obj: Dict[str, Any]) -> Any:
            """
            Deserialize this object using the outer method's keyword arguments.

            :param obj: Json description of object to be deserialized
            :return: Deserialized object
            """
            return Serialization.deserialize(obj, **kwargs)

        return list(map(deserialize, json_obj["serialized_elements"]))

    @staticmethod
    def dict_deserialize(json_obj: Dict[str, Any], **kwargs: Any) -> Dict[Any, Any]:
        """
        Function for deserializing a dictionary.

        :param json_obj: object to deserialize
        :param kwargs: optional extra keyword arguments
        :return: deserialized dictionary of which the contents have also been deserialized
        """
        return dict(
            zip(
                json_obj["keys"],
                Serialization.deserialize(json_obj["values"], **kwargs),
            )
        )

    @staticmethod
    def default_deserialize(json_obj: Dict[str, Any], **kwargs: Any) -> Any:
        """
        Fall-back function is case no specific deserialization function is available.
        This function uses the pickle library

        :param json_obj: object to deserialize
        :param kwargs: optional extra keyword arguments
        :return: deserialized object
        """
        return pickle.loads(Serialization.bytes_deserialize(json_obj["dump"], **kwargs))

    @staticmethod
    def collection_deserialize(
        json_obj: Dict[str, Any],
        **kwargs: Any,
    ) -> Union[Dict[Any, Any], List[Any], Any]:
        """
        Function for deserializing collections

        The class tree is recursed in the same order as the original collection was processed
        during serialization. Every time a 'leaf' is encountered, the keys are identified for the
        respective type and for each key, the first element of the list is extracted. These values
        are then used to deserialize the type.

        :param json_obj: object to deserialize
        :param kwargs: optional extra keyword arguments
        :raise ValueError: raised when (nested) value cannot be deserialized
        :return: deserialized collection
        """
        class_tree = json_obj["class_tree"]
        # If the class tree is a list, we need to recursively deserialize
        if isinstance(class_tree, list):
            result_list: List[Any] = []
            for entry in class_tree:
                sub_json = {"class_tree": entry, "keys": json_obj["keys"]}
                deserialized_element = Serialization.collection_deserialize(
                    sub_json, **kwargs
                )
                # if entry is a compressed list, we need to unpack the deserialized objects
                # otherwise we can simply add them to the list containing the result
                if isinstance(entry, tuple) and len(entry) == 2:
                    result_list.extend(deserialized_element)
                else:
                    result_list.append(deserialized_element)
            return result_list

        # If the element is a tuple, it can be either a compressed list or a dictionary
        if isinstance(class_tree, tuple):
            # If the element is a tuple with the 'dict' tag, recursively deserialize the lists
            # for the keys and the values and combine them into a dictionary
            if len(class_tree) == 3:
                tag, keys, values = class_tree
                assert tag == "dict"
                json_keys = {"class_tree": keys, "keys": json_obj["keys"]}
                deserialized_keys = Serialization.collection_deserialize(
                    json_keys, **kwargs
                )
                json_values = {"class_tree": values, "keys": json_obj["keys"]}
                deserialized_values = Serialization.collection_deserialize(
                    json_values, **kwargs
                )
                return dict(zip(deserialized_keys, deserialized_values))

            # If the element is a compressed list, recurse over the compressed list
            if len(class_tree) == 2:
                element_type, number = class_tree
                result_list = []
                for _ in range(number):
                    json_element = {
                        "class_tree": element_type,
                        "keys": json_obj["keys"],
                    }
                    # deserialize the inner element
                    deserialized_element = Serialization.collection_deserialize(
                        json_element,
                        **kwargs,
                    )
                    # add it to the result
                    result_list.append(deserialized_element)
                return result_list
            # else
            raise ValueError("This value cannot be deserialized")

        # If the element is a single object, find the appropriate keys and apply regular
        # deserialization
        class_name = class_tree
        data = {}
        for key in json_obj["keys"]:
            if key.startswith(class_name):
                # the keys are always of the format [class name]_[key name]
                # len(class_name) + 1 is the length of the string before
                # the actual name of the key
                clean_key = key[len(class_name) + 1 :]
                # pop the first value and write it to the right key
                data[clean_key] = json_obj["keys"][key][0]
                json_obj["keys"][key] = json_obj["keys"][key][1:]
        return Serialization.deserialize({"type": class_name, "data": data}, **kwargs)

    @staticmethod
    def deserialize(json_obj: Dict[str, Any], **kwargs: Any) -> Any:
        """
        Function that detects which deserialization function should be run and calls it

        :param json_obj: object to deserialize
        :param kwargs: optional extra keyword arguments
        :return: deserialized object
        """
        deserialization_funcs: Dict[
            str, Callable[[Arg(Dict[str, Any], "json_obj"), KwArg(Any)], Any]
        ] = {
            "int": Serialization.standard_deserialize,
            "float": Serialization.standard_deserialize,
            "bytes": Serialization.bytes_deserialize,
            "str": Serialization.standard_deserialize,
            "list": Serialization.collection_deserialize,
            "tuple": lambda j, **l_kwargs: tuple(
                Serialization.collection_deserialize(j, **l_kwargs)
            ),
            "ndarray": lambda j, **l_kwargs: np.array(
                Serialization.collection_deserialize(j, **l_kwargs)
            ),
            "dict": Serialization.collection_deserialize,
        }

        if json_obj["type"] in Serialization.new_deserialization_funcs:
            deserialization_func = Serialization.new_deserialization_funcs[
                json_obj["type"]
            ]
        elif json_obj["type"] in deserialization_funcs:
            deserialization_func = deserialization_funcs[json_obj["type"]]
        else:
            deserialization_func = Serialization.default_deserialize

        return deserialization_func(json_obj["data"], **kwargs)

    # endregion

    @staticmethod
    def unpack(json_obj: Dict[str, Any], **kwargs: Any) -> Tuple[str, Any]:
        """
        Function that handles metadata and turns the json object into a python object

        :param json_obj: json object to unpack
        :param kwargs: optional extra keyword arguments
        :return: unpacked object
        """
        msg_id = json_obj["id"]
        del json_obj["id"]
        obj = Serialization.deserialize(json_obj, **kwargs)
        return msg_id, obj


class MultiDimensionalArrayEncoder(json.JSONEncoder):
    """
    Class that represents a JSON encoder that can additionally handle collections like tuples, lists
    and dictionaries
    """

    def encode(self, o: Any) -> str:
        """
        Function that encodes a python object

        :param o: python object
        :return: the object encoded in a string
        """

        def preprocess(item: Any) -> Any:
            """
            Function that preprocesses the item to be encoded so that the general JSON encoder
            can further process it

            :param item: a collection (tuple, list or dictionary)
            :return: dictionary or list
            """
            if isinstance(item, tuple):
                if len(item) == 2:
                    class_tree, count = item
                    return {
                        "__type__": "tuple",
                        "count": count,
                        "class_tree": preprocess(class_tree),
                    }
                # else
                assert len(item) == 3
                _, keys, values = item
                return {
                    "__type__": "dict",
                    "keys": preprocess(keys),
                    "values": preprocess(values),
                }
            if isinstance(item, list):
                return [preprocess(e) for e in item]
            if isinstance(item, dict):
                return {key: preprocess(value) for key, value in item.items()}
            # else
            return item

        # Apply the preprocessing step and then call the general encoder
        return super().encode(preprocess(o))


def hinted_tuple_hook(obj: Any) -> Any:
    """
    Object hook for tuples and dictionaries which is used in json.loads

    :param obj: json object
    :return: tuple containing elements to recreate a collection
    """
    if "__type__" in obj:
        if obj["__type__"] == "tuple":
            return obj["class_tree"], obj["count"]
        # else
        assert obj["__type__"] == "dict"
        return "dict", obj["keys"], obj["values"]
    # else
    return obj


class AnnotationError(Exception):
    """
    Raised when an improperly function is incorrectly annotated
    """


class RepetitionError(Exception):
    """
    Raised when the action has already been performed and should not be repeated
    """
