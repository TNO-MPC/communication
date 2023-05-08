"""
This module tests packing and unpacking of objects
(serialization/deserialization)
"""

import copy
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

import bitarray
import numpy as np
import numpy.typing as npt
import ormsgpack
import pandas as pd
import pytest

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
    use_pickle: bool = False,
    serial_option: Optional[int] = None,
    deserial_option: Optional[int] = None,
    **kwargs: Any,
) -> None:
    r"""
    Tests packing and unpacking of an object

    :param obj: the object to pack/unpack
    :param comparator: function comparing two objects, returning True
        if they are equal
    :param expect: expected result of comparison
    :param use_pickle: set to true if one wishes to use pickle as a fallback deserializer
    :param serial_option: ormsgpack option for serialization
    :param deserial_option: ormsgpack option for deserialization
    :param \**kwargs: optional extra keyword arguments
    """
    msg_id = "test_id"
    obj_copy = copy.deepcopy(obj)
    msg_id_prime, obj_prime = Serialization.unpack(
        Serialization.pack(
            obj, msg_id, use_pickle=use_pickle, option=serial_option, **kwargs
        ),
        use_pickle=use_pickle,
        option=deserial_option,
        **kwargs,
    )
    obj = obj_copy
    assert comparator(obj, obj_prime) == expect and msg_id == msg_id_prime


def test_pickle() -> None:
    """
    Tests packing and unpacking of unsupported types through pickle
    """
    pack_unpack_test(
        Decimal(42),
        use_pickle=True,
    )


def test_pickle_fail() -> None:
    """
    Tests packing and unpacking of unsupported types through pickle
    """
    with pytest.raises(TypeError):
        pack_unpack_test(
            Decimal(42),
            use_pickle=False,
        )


def test_int64_serialization() -> None:
    """
    Tests packing and unpacking of 64-bit ints
    """
    pack_unpack_test(1, serial_option=None)


def test_int64_serialization_with_opt() -> None:
    """
    Tests packing and unpacking of 64-bit ints
    """
    pack_unpack_test(1, serial_option=ormsgpack.OPT_PASSTHROUGH_BIG_INT)


def test_int_serialization() -> None:
    """
    Tests packing and unpacking of Python ints
    """
    pack_unpack_test(2**2048 - 1, serial_option=ormsgpack.OPT_PASSTHROUGH_BIG_INT)


def test_neg_int_serialization() -> None:
    """
    Tests packing and unpacking of Python ints
    """
    pack_unpack_test(-(2**2048 - 1), serial_option=ormsgpack.OPT_PASSTHROUGH_BIG_INT)


def test_int_serialization_fail() -> None:
    """
    Tests packing and unpacking of Python ints
    """
    with pytest.raises(TypeError):
        pack_unpack_test(2**2048, serial_options=None)


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


def test_bitarray_numpy_serialization() -> None:
    """
    Tests packing and unpacking of bitarrays
    """
    array: npt.NDArray[np.object_] = np.empty([4, 3], dtype=np.object_)
    array[:] = [[bitarray.bitarray("10101110")] * 3] * 4
    pack_unpack_test(
        np.asarray(array),
        comparator=np.array_equal,
        serial_option=ormsgpack.OPT_SERIALIZE_NUMPY,
    )


def test_bitarray_serialization() -> None:
    """
    Tests packing and unpacking of numpy bitarrays
    """
    pack_unpack_test(bitarray.bitarray("10101110"))


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


def test_tuple_to_list() -> None:
    """
    Tests packing and unpacking of tuples without OPT_PASSTHROUGH_TUPLE
    """
    tuple_ = (42,)
    pack_unpack_test(tuple_, comparator=lambda a, b: a == tuple(b))


def test_empty_tuple() -> None:
    """
    Tests packing and unpacking of empty tuples
    """
    tuple_ = ()
    pack_unpack_test(tuple_, serial_option=ormsgpack.OPT_PASSTHROUGH_TUPLE)


def test_tuple_serialization_same_type() -> None:
    """
    Tests packing and unpacking of tuples with objects of same type
    """
    tuple_ = (1, 2, 3, 4, 5)
    pack_unpack_test(tuple_, serial_option=ormsgpack.OPT_PASSTHROUGH_TUPLE)


def test_tuple_serialization_dif_type() -> None:
    """
    Tests packing and unpacking of tuples with objects of different type
    """
    tuple_ = (1, 2.0, "3", [4], (5,))
    pack_unpack_test(tuple_, serial_option=ormsgpack.OPT_PASSTHROUGH_TUPLE)


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


def test_dict_serialization_non_str() -> None:
    """
    Tests packing and unpacking of dictionary with non-string keys
    """
    dict_ = {1: 1, "2": 2}
    pack_unpack_test(
        dict_,
        serial_option=ormsgpack.OPT_NON_STR_KEYS,
        deserial_option=ormsgpack.OPT_NON_STR_KEYS,
    )


def test_dict_serialization_multiple_non_str() -> None:
    """
    Tests packing and unpacking of dictionary with multiple different value types
     with non-string keys
    """
    dict_ = {"1": 1, 2: "2", 3: 3.0}
    pack_unpack_test(
        dict_,
        serial_option=ormsgpack.OPT_NON_STR_KEYS,
        deserial_option=ormsgpack.OPT_NON_STR_KEYS,
    )


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
    pack_unpack_test(
        collection,
        serial_option=ormsgpack.OPT_PASSTHROUGH_TUPLE | ormsgpack.OPT_NON_STR_KEYS,
        deserial_option=ormsgpack.OPT_NON_STR_KEYS,
    )


def test_empty_ndarray_serialization() -> None:
    """
    Tests packing and unpacking of an empty numpy array
    """
    array_: npt.NDArray[np.object_] = np.empty([0, 3], dtype=np.object_)
    pack_unpack_test(
        array_, np.array_equal, serial_option=ormsgpack.OPT_SERIALIZE_NUMPY
    )


def test_ndarray_serialization() -> None:
    """
    Tests packing and unpacking of a numpy array
    """
    array_: npt.NDArray[np.int_] = np.array([[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
    pack_unpack_test(
        array_, np.array_equal, serial_option=ormsgpack.OPT_SERIALIZE_NUMPY
    )


def test_zero_dimensional_zero_value_ndarray_serialization() -> None:
    """
    Tests packing and unpacking of a zero-dimensional array with scalar zero

    This results in a different path than a non-zero scalar
    """
    array = np.array(0)
    pack_unpack_test(array, comparator=np.array_equal)


def test_zero_dimensional_nonzero_value_ndarray_serialization() -> None:
    """
    Tests packing and unpacking of a zero-dimensional array with non-zero scalar

    This results in a different path than a zero-valued scalar
    """
    array = np.array(391)
    pack_unpack_test(array, comparator=np.array_equal)


def test_custom_serialization_no_logic() -> None:
    """
    Tests whether an AttributeError exception is raised when custom
    serialization logic is missing
    """
    Serialization.clear_serialization_logic()
    with pytest.raises(AttributeError):
        Serialization.register_class(ClassNoLogic)  # type: ignore[arg-type]


def test_empty_series_serialization() -> None:
    """
    Tests packing and unpacking of an empty pandas series
    """
    dataframe = pd.Series(dtype=object)
    pack_unpack_test(dataframe, lambda df1, df2: df1.equals(df2))


def test_series_serialization() -> None:
    """
    Tests packing and unpacking of a pandas series
    """
    dataframe = pd.Series([1, 2, 3], index=["a", "b", "c"])
    pack_unpack_test(dataframe, lambda df1, df2: df1.equals(df2))


def test_empty_dataframe_serialization() -> None:
    """
    Tests packing and unpacking of an empty pandas dataframe
    """
    dataframe = pd.DataFrame()
    pack_unpack_test(dataframe, lambda df1, df2: df1.equals(df2))


def test_dataframe_serialization() -> None:
    """
    Tests packing and unpacking of a pandas dataframe
    """
    dataframe = pd.DataFrame(
        {
            "integers": [1, 2, 3],
            "strings": "str_value",
            "includes_none": [None, 2, 3],
            "datetime": datetime.now(),
            "bigint": 2**128,
        },
        index=["a", "b", "c"],
    )
    pack_unpack_test(dataframe, lambda df1, df2: df1.equals(df2))


def test_custom_serialization_no_functions() -> None:
    """
    Tests whether a TypeError exception is raised when custom  serialization
    functions are missing
    """
    Serialization.clear_serialization_logic()
    with pytest.raises(TypeError):
        Serialization.register_class(ClassNoFunctions)  # type: ignore[arg-type]


def test_custom_serialization_wrong_signature() -> None:
    """
    Tests whether a TypeError exception is raised when deserialization
    functions have wrong signature
    """
    Serialization.clear_serialization_logic()
    with pytest.raises(TypeError):
        Serialization.register_class(ClassWrongSignature)


def test_custom_serialization_mismatch_type() -> None:
    """
    Tests whether an AnnotationError exception is raised when deserialization
    functions 'obj' and serialization return type mismatch
    """
    Serialization.clear_serialization_logic()
    with pytest.raises(AnnotationError):
        Serialization.register_class(ClassMismatchType)


def test_custom_serialization_no_annotation() -> None:
    """
    Tests whether an AnnotationError exception is raised when serialization
    functions are not annotated
    """
    Serialization.clear_serialization_logic()
    with pytest.raises(AnnotationError):
        Serialization.register_class(ClassNoAnnotation)


def test_custom_serialization_correct_double() -> None:
    """
    Tests whether a RepetitionError exception is raised when serialization
    functions is set twice
    """
    Serialization.clear_serialization_logic()
    with pytest.raises(RepetitionError):
        Serialization.register_class(ClassCorrect)
        # setting logic twice makes no sense. This should return a RepetitionError
        Serialization.register_class(ClassCorrect)
        obj = ClassCorrect(1)
        pack_unpack_test(obj, lambda a, b: a.value == b.value)


def test_custom_serialization_no_kwargs() -> None:
    """
    Tests whether a TypeError exception is raised when serialization functions do not include the
    **kwargs keyword.
    """
    Serialization.clear_serialization_logic()
    with pytest.raises(TypeError):
        Serialization.register_class(ClassNoKwargs)  # type: ignore[arg-type]


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


class ClassWrongSignature(SupportsSerialization):
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
        r"""
        Serialization method

        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return self.value

    @staticmethod
    def deserialize(value: int, **_kwargs: Any) -> "ClassWrongSignature":  # type: ignore[override]  # pylint: disable=arguments-renamed
        r"""
        Deserialization method

        :param \**_kwargs: optional extra keyword arguments
        :param value: object to deserialize
        :return: deserializes object
        """
        return ClassWrongSignature(value)


class ClassNoAnnotation(SupportsSerialization):
    """
    Class that implements serialization logic without annotation
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs):  # type: ignore[no-untyped-def]
        r"""
        Serialization method

        :param \**_kwargs: optional extra keyword arguments
        :type \**_kwargs: Any
        :return: serialized object
        :rtype: dict
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(obj, **_kwargs):  # type: ignore[no-untyped-def]
        r"""
        Deserialization method

        :param obj: object to deserialize
        :type obj: dict
        :param \**_kwargs: optional extra keyword arguments
        :type \**_kwargs: Any
        :return: deserializes object
        :rtype: ClassNoAnnotation
        """
        return ClassNoAnnotation(obj["value"])


class ClassMismatchType(SupportsSerialization):
    """
    Class that implements serialization logic incorrectly
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs: Any) -> Dict[str, int]:
        r"""
        Serialization method

        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(obj: Any, **_kwargs: Any) -> "ClassMismatchType":
        r"""
        Deserialization method

        :param obj: object to deserialize
        :param \**_kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassMismatchType(obj["value"])


class ClassCorrect(SupportsSerialization):
    """
    Class that implements serialization logic correctly
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs: Any) -> Dict[str, int]:
        r"""
        Serialization method

        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(obj: Dict[str, int], **_kwargs: Any) -> "ClassCorrect":
        r"""
        Deserialization method

        :param obj: object to deserialize
        :param \**_kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassCorrect(obj["value"])


class ClassCorrect2:
    """
    Class that implements serialization logic correctly
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs: "Any") -> "dict":  # type: ignore[type-arg]
        r"""
        Serialization method

        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(obj: "dict", **_kwargs: "Any") -> "ClassCorrect2":  # type: ignore[type-arg]
        r"""
        Deserialization method

        :param obj: object to deserialize
        :param \**_kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassCorrect2(obj["value"])


class ClassCorrect3:
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

    def serialize(self, **_kwargs: "Any") -> Union[bytes, Dict[str, bytes]]:
        r"""
        Serialization method

        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return Serialization.serialize(
            {
                "values": self.values,
                "name": self.name,
            },
            use_pickle=True,
        )

    @staticmethod
    def deserialize(
        obj: Union[bytes, Dict[str, bytes]], **_kwargs: "Any"
    ) -> "ClassCorrect3":
        r"""
        Deserialization method

        :param obj: object to deserialize
        :param \**_kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        dict_obj = Serialization.deserialize(obj, use_pickle=True)
        return ClassCorrect3(dict_obj["values"], dict_obj["name"])


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
            "values": self.values,
            "name": self.name,
        }

    @staticmethod
    def deserialize(obj: Dict[str, Any]) -> "ClassNoKwargs":
        """
        Deserialization method

        :param obj: object to deserialize
        :return: deserializes object
        """
        return ClassNoKwargs(obj["values"], obj["name"])


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

    def serialize(  # type: ignore[override]  # pylint: disable=arguments-differ
        self, *, destination: Union[str, HTTPClient], **kwargs: Any
    ) -> Dict[str, Any]:
        r"""
        Serialization method

        :param destination: Receiver of the message.
        :param \**kwargs: optional extra keyword arguments
        :return: serialized object
        """
        self.destination.append(destination)
        return {
            "values": self.values,
            "name": self.name,
        }

    @staticmethod
    def deserialize(  # type: ignore[override]  # pylint: disable=arguments-differ
        obj: Dict[str, Any],
        *,
        origin: Union[str, HTTPClient],
        **kwargs: Any,
    ) -> "ClassCorrectKwargs":
        r"""
        Deserialization method

        :param obj: object to deserialize
        :param origin: Sender of the message.
        :param \**kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        ClassCorrectKwargs.origin.append(origin)
        return ClassCorrectKwargs(obj["values"], obj["name"])


class ClassCorrectKwargs2:
    """
    Class that implements correct serialization logic making use of additional keyword arguments.
    """

    def __init__(self, values: List[int], other: ClassCorrectKwargs):
        self.values = values
        self.other = other

    def serialize(self, **_kwargs: Any) -> Dict[str, Any]:
        r"""
        Serialization method

        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {
            "values": self.values,
            "other": self.other,
        }

    @staticmethod
    def deserialize(obj: Dict[str, Any], **_kwargs: Any) -> "ClassCorrectKwargs2":
        r"""
        Deserialization method

        :param obj: object to deserialize
        :param \**_kwargs: optional extra keyword arguments
        :return: deserializes object
        """
        return ClassCorrectKwargs2(obj["values"], obj["other"])


@pytest.mark.parametrize("correct_class", (ClassCorrect, ClassCorrect2))
def test_custom_serialization_correct(
    correct_class: Type[Union[ClassCorrect, ClassCorrect2]]
) -> None:
    """
    Tests correctly implemented serialization logic

    :param correct_class: a correctly implemented serialization class
    """
    Serialization.clear_serialization_logic()
    Serialization.register_class(correct_class)
    obj = correct_class(1)
    pack_unpack_test(obj, lambda a, b: a.value == b.value)


@pytest.mark.parametrize(
    "correct_class, correct_class_2",
    (
        (ClassCorrect2, ClassCorrect3),
        (ClassCorrect, ClassCorrect3),
    ),
)
def test_custom_serialization_correct2(
    correct_class: Type[Union[ClassCorrect, ClassCorrect2]],
    correct_class_2: Type[ClassCorrect3],
) -> None:
    """
    Tests correctly implemented serialization logic

    :param correct_class: a correctly implemented serialization class
    :param correct_class_2: a correctly implemented serialization class
    """
    Serialization.clear_serialization_logic()
    Serialization.register_class(correct_class)
    Serialization.register_class(correct_class_2)
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
    Serialization.clear_serialization_logic()
    Serialization.register_class(ClassCorrectKwargs)
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
    Serialization.clear_serialization_logic()
    Serialization.register_class(ClassCorrectKwargs)
    Serialization.register_class(ClassCorrectKwargs2)
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


def test_ndarray_custom_logic_elements_serialization() -> None:
    """
    Tests packing and unpacking of a numpy array with custom-serialized elements
    """
    Serialization.clear_serialization_logic()
    array_: npt.NDArray[np.int_] = np.array([ClassCorrect(1)])

    def compare(arr1: npt.NDArray[Any], arr2: npt.NDArray[Any]) -> bool:
        """
        Check two numpy arrays that contain a single ClassCorrect element for equality

        :param arr1: first array
        :param arr2: second array
        :return: True if the ClassCorrect elements have the same value
        """

        return cast(bool, arr1[0].value == arr2[0].value)

    with pytest.raises(
        TypeError, match="Type is not msgpack serializable: ClassCorrect"
    ):
        pack_unpack_test(
            array_,
            compare,
            serial_option=ormsgpack.OPT_SERIALIZE_NUMPY,
            use_pickle=False,
        )
    Serialization.register_class(ClassCorrect)
    pack_unpack_test(
        array_,
        compare,
        serial_option=ormsgpack.OPT_SERIALIZE_NUMPY,
        use_pickle=False,
    )
