"""
This module tests packing and unpacking of objects
(serialization/deserialization)
"""

import copy
from typing import Any, Callable, Dict, List, Type, TypeVar, Union

import pytest
from numpy import array, array_equal

from tno.mpc.communication import (
    AnnotationError,
    RepetitionError,
    Serialization,
    SupportsSerialization,
)
from tno.mpc.communication.httphandlers import HTTPClient

TypePlaceholder = TypeVar("TypePlaceholder")


def pack_unpack_test(
    obj: TypePlaceholder,
    comparator: Callable[[TypePlaceholder, TypePlaceholder], bool] = lambda a, b: a
    == b,
    expect: bool = True,
    **kwargs: Any,
) -> None:
    """
    Tests packing and unpacking of an object

    :param obj: the object to pack/unpack
    :param comparator: function comparing two objects, returning True
        if they are equal
    :param kwargs: optional extra keyword arguments
    :param expect: expected result of comparison
    """
    msg_id = "test_id"
    obj_copy = copy.deepcopy(obj)
    msg_id_prime, obj_prime = Serialization.unpack(
        Serialization.pack(obj, msg_id, **kwargs), **kwargs
    )
    obj = obj_copy
    assert comparator(obj, obj_prime) == expect and msg_id == msg_id_prime


def test_int_serialization() -> None:
    """
    Tests packing and unpacking of ints
    """
    pack_unpack_test(1)


def test_float_serialization() -> None:
    """
    Tests packing and unpacking of floats
    """
    pack_unpack_test(1.0)


def test_str_serialization() -> None:
    """
    Tests packing and unpacking of strings
    """
    pack_unpack_test("test string")


def test_bytes_serialization() -> None:
    """
    Tests packing and unpacking of bytes
    """
    pack_unpack_test(b"10101")


def test_empty_list() -> None:
    """
    Tests packing and unpacking of empty lists
    """
    list_: List[None] = []
    pack_unpack_test(list_)


def test_list_serialization_same_type() -> None:
    """
    Tests packing and unpacking of lists with objects of same type
    """
    list_ = [1, 2, 3, 4, 5]
    pack_unpack_test(list_)


def test_list_serialization_dif_type() -> None:
    """
    Tests packing and unpacking of lists with objects of different type
    """
    list_ = [1, 2.0, "3", [4]]
    pack_unpack_test(list_)


def test_empty_tuple() -> None:
    """
    Tests packing and unpacking of empty tuples
    """
    tuple_ = ()
    pack_unpack_test(tuple_)


def test_tuple_serialization_same_type() -> None:
    """
    Tests packing and unpacking of tuples with objects of same type
    """
    tuple_ = (1, 2, 3, 4, 5)
    pack_unpack_test(tuple_)


def test_tuple_serialization_dif_type() -> None:
    """
    Tests packing and unpacking of tuples with objects of different type
    """
    tuple_ = (1, 2.0, "3", [4], (5,))
    pack_unpack_test(tuple_)


def test_dict_serialization() -> None:
    """
    Tests packing and unpacking of dictionary
    """
    dict_ = {"1": 1, "2": 2}
    pack_unpack_test(dict_)


def test_dict_serialization_multiple() -> None:
    """
    Tests packing and unpacking of dictionary with multiple different value types
    """
    dict_ = {"1": 1, "2": "2", "3": 3.0}
    pack_unpack_test(dict_)


def test_empty_dict() -> None:
    """
    Tests packing and unpacking of empty dictionary
    """
    dict_: Dict[Any, Any] = {}
    pack_unpack_test(dict_)


def test_monstrous_collection_serialization() -> None:
    """
    Tests packing and unpacking of a complex collection
    """
    collection = [
        [[1, 2], [3, 4], "5", 6],
        "7",
        "z",
        {"8": 9, 10: "11", 12.1: 13.2},
        {"14": 15, 16: "17", 18.1: 19.2},
        [[[20], "21", 22.1], "13"],
        ([1, 2], "3", 3.0, {"4": 5.0}, (6, 7)),
    ]
    pack_unpack_test(collection)


def test_ndarray_serialization() -> None:
    """
    Tests packing and unpacking of a numpy array
    """
    array_ = array([1, 2, 3, 4, 5])
    pack_unpack_test(array_, array_equal)


def test_custom_serialization_no_logic() -> None:
    """
    Tests whether an AttributeError exception is raised when custom
    serialization logic is missing
    """
    Serialization.clear_new_serialization_logic()
    with pytest.raises(AttributeError):
        Serialization.set_serialization_logic(ClassNoLogic)  # type: ignore


def test_custom_serialization_no_functions() -> None:
    """
    Tests whether a TypeError exception is raised when custom  serialization
    functions are missing
    """
    Serialization.clear_new_serialization_logic()
    with pytest.raises(TypeError):
        Serialization.set_serialization_logic(ClassNoFunctions)  # type: ignore


def test_custom_serialization_wrong_annotation() -> None:
    """
    Tests whether an AnnotationError exception is raised when serialization
    functions are wrongly annotated
    """
    Serialization.clear_new_serialization_logic()
    with pytest.raises(AnnotationError):
        Serialization.set_serialization_logic(ClassWrongAnnotation)  # type: ignore


def test_custom_serialization_no_annotation() -> None:
    """
    Tests whether an AnnotationError exception is raised when serialization
    functions are not annotated
    """
    Serialization.clear_new_serialization_logic()
    with pytest.raises(AnnotationError):
        Serialization.set_serialization_logic(ClassNoAnnotation)


def test_custom_serialization_correct_double() -> None:
    """
    Tests whether a RepetitionError exception is raised when serialization
    functions is set twice
    """
    Serialization.clear_new_serialization_logic()
    with pytest.raises(RepetitionError):
        Serialization.set_serialization_logic(ClassCorrect)
        # setting logic twice makes no sense. This should return a RepetitionError
        Serialization.set_serialization_logic(ClassCorrect)
        obj = ClassCorrect(1)
        pack_unpack_test(obj, lambda a, b: a.value == b.value)


def test_custom_serialization_no_kwargs() -> None:
    """
    Tests whether a TypeError exception is raised when serialization functions do not include the
    **kwargs keyword.
    """
    Serialization.clear_new_serialization_logic()
    with pytest.raises(TypeError):
        Serialization.set_serialization_logic(ClassNoKwargs)  # type: ignore


class ClassNoLogic:
    """
    Class that implements no serialization logic
    """

    # pylint: disable=too-few-public-methods

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value


class ClassNoFunctions:
    """
    Class that implements no serialization functions
    """

    # pylint: disable=too-few-public-methods

    serialize = 0
    deserialize = 0

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value


class ClassWrongAnnotation:
    """
    Class that implements serialization logic with wrong annotation
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs: Any) -> int:
        """
        Serialization method

        :param _kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return self.value

    @staticmethod
    def deserialize(value: Dict[str, Any], **_kwargs: Any) -> "ClassWrongAnnotation":
        """
        Deserialization method

        :param _kwargs: optional extra keyword arguments
        :param value: object to deserialize
        :return: deserializes object
        """
        return ClassWrongAnnotation(value)  # type: ignore


class ClassNoAnnotation:
    """
    Class that implements serialization logic without annotation
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs):  # type: ignore
        """
        Serialization method

        :param _kwargs: optional extra keyword arguments
        :type _kwargs: Any
        :return: serialized object
        :rtype: dict
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(json_obj, **_kwargs):  # type: ignore
        """
        Deserialization method

        :param json_obj: object to deserialize
        :type json_obj: dict
        :param _kwargs: optional extra keyword arguments
        :type _kwargs: Any
        :return: deserializes object
        :rtype: ClassNoAnnotation
        """
        return ClassNoAnnotation(json_obj["value"])


class ClassCorrect:
    """
    Class that implements serialization logic correctly
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs: Any) -> dict:  # type: ignore
        """
        Serialization method

        :param _kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(json_obj: dict, **_kwargs: Any) -> "ClassCorrect":  # type: ignore
        """
        Deserialization method

        :param json_obj: object to deserialize
        :param _kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassCorrect(json_obj["value"])


class ClassCorrect2:
    """
    Class that implements serialization logic correctly
    """

    def __init__(self, values: List[int], name: str) -> None:
        """
        Initialization of class

        :param values: list of values; values attribute of class
        :param name: name attribute of class
        """
        self.values = values
        self.name = name

    def serialize(self, **_kwargs: Any) -> Dict[str, Any]:
        """
        Serialization method

        :param _kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {
            "values": Serialization.serialize(self.values),
            "name": Serialization.serialize(self.name),
        }

    @staticmethod
    def deserialize(json_obj: Dict[str, Any], **_kwargs: Any) -> "ClassCorrect2":
        """
        Deserialization method

        :param json_obj: object to deserialize
        :param _kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassCorrect2(
            Serialization.deserialize(json_obj["values"]),
            Serialization.deserialize(json_obj["name"]),
        )


class ClassCorrect3:
    """
    Class that implements serialization logic correctly
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs: "Any") -> "dict":  # type: ignore
        """
        Serialization method

        :param _kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(json_obj: "dict", **_kwargs: "Any") -> "ClassCorrect3":  # type: ignore
        """
        Deserialization method

        :param json_obj: object to deserialize
        :param _kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassCorrect3(json_obj["value"])


class ClassCorrect4:
    """
    Class that implements serialization logic correctly
    """

    def __init__(self, values: List[int], name: str) -> None:
        """
        Initialization of class

        :param values: list of values; values attribute of class
        :param name: name attribute of class
        """
        self.values = values
        self.name = name

    def serialize(self, **_kwargs: "Any") -> "Dict[str, Any]":
        """
        Serialization method

        :param _kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {
            "values": Serialization.serialize(self.values),
            "name": Serialization.serialize(self.name),
        }

    @staticmethod
    def deserialize(json_obj: "Dict[str, Any]", **_kwargs: "Any") -> "ClassCorrect4":
        """
        Deserialization method

        :param json_obj: object to deserialize
        :param _kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassCorrect4(
            Serialization.deserialize(json_obj["values"]),
            Serialization.deserialize(json_obj["name"]),
        )


class ClassNoKwargs:
    """
    Class that implements correct serialization logic but doesn't use optional keyword arguments.
    """

    def __init__(self, values: List[int], name: str) -> None:
        """
        Initialization of class

        :param values: list of values; values attribute of class
        :param name: name attribute of class
        """
        self.values = values
        self.name = name

    def serialize(self) -> Dict[str, Any]:
        """
        Serialization method

        :return: serialized object
        """
        return {
            "values": Serialization.serialize(self.values),
            "name": Serialization.serialize(self.name),
        }

    @staticmethod
    def deserialize(json_obj: Dict[str, Any]) -> "ClassNoKwargs":
        """
        Deserialization method

        :param json_obj: object to deserialize
        :return: deserializes object
        """
        return ClassNoKwargs(
            Serialization.deserialize(json_obj["values"]),
            Serialization.deserialize(json_obj["name"]),
        )


class ClassCorrectKwargs(SupportsSerialization):
    """
    Class that implements correct serialization logic making use of additional keyword arguments.
    """

    origin: List[Union[str, HTTPClient]] = []
    destination: List[Union[str, HTTPClient]] = []

    def __init__(
        self, values: List[int], name: str
    ):  # pylint: disable=super-init-not-called
        self.values = values
        self.name = name

    def serialize(  # type: ignore  # pylint: disable=arguments-differ
        self, *, destination: Union[str, HTTPClient], **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Serialization method

        :param destination: Receiver of the message.
        :param kwargs: optional extra keyword arguments
        :return: serialized object
        """
        self.destination.append(destination)
        return {
            "values": Serialization.serialize(self.values, **kwargs),
            "name": Serialization.serialize(self.name, **kwargs),
        }

    @staticmethod
    def deserialize(  # type: ignore  # pylint: disable=arguments-differ
        json_obj: Dict[str, Any], *, origin: Union[str, HTTPClient], **kwargs: Any
    ) -> "ClassCorrectKwargs":
        """
        Deserialization method

        :param json_obj: object to deserialize
        :param origin: Sender of the message.
        :param kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        ClassCorrectKwargs.origin.append(origin)
        return ClassCorrectKwargs(
            Serialization.deserialize(json_obj["values"], **kwargs),
            Serialization.deserialize(json_obj["name"], **kwargs),
        )


class ClassCorrectKwargs2:
    """
    Class that implements correct serialization logic making use of additional keyword arguments.
    """

    def __init__(self, values: List[int], other: ClassCorrectKwargs):
        self.values = values
        self.other = other

    def serialize(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Serialization method

        :param kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {
            "values": Serialization.serialize(self.values, **kwargs),
            "other": Serialization.serialize(self.other, **kwargs),
        }

    @staticmethod
    def deserialize(json_obj: Dict[str, Any], **kwargs: Any) -> "ClassCorrectKwargs2":
        """
        Deserialization method

        :param json_obj: object to deserialize
        :param kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassCorrectKwargs2(
            Serialization.deserialize(json_obj["values"], **kwargs),
            Serialization.deserialize(json_obj["other"], **kwargs),
        )


@pytest.mark.parametrize("correct_class", (ClassCorrect, ClassCorrect3))
def test_custom_serialization_correct(
    correct_class: Type[Union[ClassCorrect, ClassCorrect3]]
) -> None:
    """
    Tests correctly implemented serialization logic

    :param correct_class: a correctly implemented serialization class
    """
    Serialization.clear_new_serialization_logic()
    Serialization.set_serialization_logic(correct_class)
    obj = correct_class(1)
    pack_unpack_test(obj, lambda a, b: a.value == b.value)


@pytest.mark.parametrize(
    "correct_class, correct_class_2",
    (
        (ClassCorrect, ClassCorrect2),
        (ClassCorrect3, ClassCorrect4),
        (ClassCorrect, ClassCorrect4),
        (ClassCorrect3, ClassCorrect2),
    ),
)
def test_custom_serialization_correct2(
    correct_class: Type[Union[ClassCorrect, ClassCorrect3]],
    correct_class_2: Type[Union[ClassCorrect2, ClassCorrect4]],
) -> None:
    """
    Tests correctly implemented serialization logic

    :param correct_class: a correctly implemented serialization class
    :param correct_class_2: a correctly implemented serialization class
    """
    Serialization.clear_new_serialization_logic()
    Serialization.set_serialization_logic(correct_class)
    Serialization.set_serialization_logic(correct_class_2)
    obj = correct_class(1)
    pack_unpack_test(obj, lambda a, b: a.value == b.value)
    obj2 = correct_class_2([1, 2, 3, 4], "test")
    pack_unpack_test(obj2, lambda a, b: a.values == b.values and a.name == b.name)


def test_custom_serialization_correct_kwargs() -> None:
    """
    Tests correctly implemented serialization logic making use of optional keyword arguments
    """
    ClassCorrectKwargs.origin = []
    ClassCorrectKwargs.destination = []
    Serialization.clear_new_serialization_logic()
    Serialization.set_serialization_logic(ClassCorrectKwargs)
    obj = ClassCorrectKwargs([1, 2, 3, 4], "test")
    pack_unpack_test(
        obj,
        lambda a, b: a.values == b.values and a.name == b.name,
        origin="origin",
        destination="destination",
    )
    assert ClassCorrectKwargs.origin == ["origin"]
    assert ClassCorrectKwargs.destination == ["destination"]
    ClassCorrectKwargs.origin = []
    ClassCorrectKwargs.destination = []


def test_custom_serialization_correct_kwargs2() -> None:
    """
    Tests correctly implemented serialization logic making use of optional keyword arguments
    """
    ClassCorrectKwargs.origin = []
    ClassCorrectKwargs.destination = []
    Serialization.clear_new_serialization_logic()
    Serialization.set_serialization_logic(ClassCorrectKwargs)
    Serialization.set_serialization_logic(ClassCorrectKwargs2)
    obj = ClassCorrectKwargs([1, 2, 3, 4], "test")
    obj2 = ClassCorrectKwargs2([5, 6, 7, 8], obj)
    pack_unpack_test(
        obj2,
        lambda a, b: a.values == b.values
        and a.other.values == b.other.values
        and a.other.name == b.other.name,
        origin="origin2",
        destination="destination2",
    )
    assert ClassCorrectKwargs.origin == ["origin2"]
    assert ClassCorrectKwargs.destination == ["destination2"]
    ClassCorrectKwargs.origin = []
    ClassCorrectKwargs.destination = []
