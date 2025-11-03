"""
This module tests packing and unpacking of objects
(serialization/deserialization)
"""

from __future__ import annotations

import copy
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, TypeVar

import bitarray
import numpy as np
import numpy.typing as npt
import ormsgpack
import pandas as pd
import pytest

try:
    import torch

    HAS_TORCH = True
except OSError as exc:
    warnings.warn(f"Failed to load torch: {exc}")
    HAS_TORCH = False

from tno.mpc.communication import (
    AnnotationError,
    RepetitionError,
    Serializer,
    SupportsSerialization,
)
from tno.mpc.communication.packers.serialization import (
    DEFAULT_PACK_OPTION,
    DEFAULT_UNPACK_OPTION,
    DeserializerOpts,
    SerializerOpts,
)

TypePlaceholder = TypeVar("TypePlaceholder")


skip_torch = pytest.mark.skipif(
    not HAS_TORCH,
    reason="skipping as importing torch raised an OSError (probably missing DLLs)",
)


def pack_unpack_test(
    obj: TypePlaceholder,
    *,
    comparator: Callable[[TypePlaceholder, TypePlaceholder], bool] = lambda a, b: a
    == b,
    expect: bool = True,
    fallback_pickle: bool = False,
    serial_option: int | None = DEFAULT_PACK_OPTION,
    deserial_option: int | None = DEFAULT_UNPACK_OPTION,
    assert_type: bool = True,
) -> None:
    """
    Tests packing and unpacking of an object

    :param obj: the object to pack/unpack
    :param comparator: function comparing two objects, returning True
        if they are equal
    :param expect: expected result of comparison
    :param fallback_pickle: set to true if one wishes to use pickle as a fallback deserializer
    :param serial_option: ormsgpack option for serialization
    :param deserial_option: ormsgpack option for deserialization
    :param assert_type: assert that the unpacked object is of the same type as the original object
    """
    obj_copy = copy.deepcopy(obj)
    obj_prime = Serializer.deserialize(
        Serializer.serialize(obj_copy, SerializerOpts(fallback_pickle, serial_option)),
        DeserializerOpts(fallback_pickle, deserial_option),
    )

    if assert_type:
        assert isinstance(obj_prime, type(obj))
    assert comparator(obj, obj_prime) == expect


def test_pickle() -> None:
    """
    Tests packing and unpacking of unsupported types through pickle
    """
    pack_unpack_test(
        Decimal(42),
        fallback_pickle=True,
    )


def test_pickle_fail() -> None:
    """
    Tests packing and unpacking of unsupported types through pickle
    """
    with pytest.raises(TypeError):
        pack_unpack_test(
            Decimal(42),
            fallback_pickle=False,
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
        pack_unpack_test(2**2048, serial_option=None)


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
    list_: list[None] = []
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
    dict_: dict[Any, Any] = {}
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
        array_, comparator=np.array_equal, serial_option=ormsgpack.OPT_SERIALIZE_NUMPY
    )


def test_ndarray_serialization() -> None:
    """
    Tests packing and unpacking of a numpy array
    """
    array_: npt.NDArray[np.int_] = np.array([[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
    pack_unpack_test(
        array_,
        comparator=np.array_equal,
        serial_option=ormsgpack.OPT_SERIALIZE_NUMPY,
        assert_type=False,
    )


def test_zero_dimensional_zero_value_ndarray_serialization() -> None:
    """
    Tests packing and unpacking of a zero-dimensional array with scalar zero

    This results in a different path than a non-zero scalar
    """
    array = np.array(0)
    pack_unpack_test(array, comparator=np.array_equal, assert_type=False)


def test_zero_dimensional_nonzero_value_ndarray_serialization() -> None:
    """
    Tests packing and unpacking of a zero-dimensional array with non-zero scalar

    This results in a different path than a zero-valued scalar
    """
    array = np.array(391)
    pack_unpack_test(array, comparator=np.array_equal, assert_type=False)


def test_custom_serialization_no_logic() -> None:
    """
    Tests whether an AttributeError exception is raised when custom
    serialization logic is missing
    """
    Serializer.clear_serialization_logic()
    with pytest.raises(AttributeError):
        Serializer.register_class(ClassNoLogic)  # type: ignore[arg-type]


def test_timestamp() -> None:
    """
    Tests packing and unpacking of a timestamp
    """
    ts = pd.Timestamp(datetime.now())
    pack_unpack_test(ts)


def test_empty_series_serialization() -> None:
    """
    Tests packing and unpacking of an empty pandas series
    """
    series: pd.Series[Any] = pd.Series(dtype=object)
    pack_unpack_test(series, comparator=lambda df1, df2: df1.equals(df2))


def test_series_serialization() -> None:
    """
    Tests packing and unpacking of a pandas series
    """
    series: pd.Series[Any] = pd.Series([1, 2, 3], index=["a", "b", "c"])
    pack_unpack_test(series, comparator=lambda df1, df2: df1.equals(df2))


def test_empty_dataframe_serialization() -> None:
    """
    Tests packing and unpacking of an empty pandas dataframe
    """
    dataframe = pd.DataFrame()
    pack_unpack_test(dataframe, comparator=lambda df1, df2: df1.equals(df2))


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
    dataframe = dataframe.astype({"datetime": "datetime64[ns]"})
    pack_unpack_test(dataframe, comparator=lambda df1, df2: df1.equals(df2))


@skip_torch
def test_empty_pytorch_tensor_serialization() -> None:
    """
    Tests packing and unpacking of an empty pytorch tensor
    """
    tensor = torch.tensor([])
    pack_unpack_test(tensor, comparator=torch.equal)


@skip_torch
def test_multidimensional_empty_pytorch_tensor_serialization() -> None:
    """
    Tests packing and unpacking of a multidimensional empty pytorch tensor
    """
    tensor = torch.tensor([[], [[]]])
    pack_unpack_test(tensor, comparator=torch.equal)


@skip_torch
def test_pytorch_tensor_serialization() -> None:
    """
    Tests packing and unpacking of a pytorch tensor
    """
    tensor = torch.tensor([[1, 2, 3], [1.5, 2.5, 3.5], [True, False, True]])
    pack_unpack_test(tensor, comparator=torch.equal)


def test_custom_serialization_no_functions() -> None:
    """
    Tests whether a TypeError exception is raised when custom  serialization
    functions are missing
    """
    Serializer.clear_serialization_logic()
    with pytest.raises(TypeError):
        Serializer.register_class(ClassNoFunctions)  # type: ignore[arg-type]


def test_custom_serialization_wrong_signature() -> None:
    """
    Tests whether a TypeError exception is raised when deserialization
    functions have wrong signature
    """
    Serializer.clear_serialization_logic()
    with pytest.raises(TypeError):
        Serializer.register_class(ClassWrongSignature)  # type: ignore[arg-type]


def test_custom_serialization_mismatch_type() -> None:
    """
    Tests whether an AnnotationError exception is raised when deserialization
    functions 'obj' and serialization return type mismatch
    """
    Serializer.clear_serialization_logic()
    with pytest.raises(AnnotationError):
        Serializer.register_class(ClassMismatchType)  # type: ignore[arg-type]


def test_custom_serialization_no_annotation() -> None:
    """
    Tests whether an AnnotationError exception is raised when serialization
    functions are not annotated
    """
    Serializer.clear_serialization_logic()
    with pytest.raises(AnnotationError):
        Serializer.register_class(ClassNoAnnotation)


def test_custom_serialization_correct_double() -> None:
    """
    Tests whether a RepetitionError exception is raised when serialization
    functions is set twice
    """
    Serializer.clear_serialization_logic()
    with pytest.raises(RepetitionError):
        Serializer.register_class(ClassCorrect)
        # setting logic twice makes no sense. This should return a RepetitionError
        Serializer.register_class(ClassCorrect)
        obj = ClassCorrect(1)
        pack_unpack_test(obj)


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


class ClassWrongSignature:
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
    def deserialize(value: int, **_kwargs: Any) -> ClassWrongSignature:
        r"""
        Deserialization method

        :param \**_kwargs: optional extra keyword arguments
        :param value: object to deserialize
        :return: deserializes object
        """
        return ClassWrongSignature(value)


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

    def serialize(self, opts):  # type: ignore[no-untyped-def]
        """
        Serialization method

        :param opts: options to change the behaviour of the serialization.
        :type opts: SerializerOpts | None
        :return: serialized object
        :rtype: dict[str, int]
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(obj, opts):  # type: ignore[no-untyped-def]
        """
        Deserialization method

        :param obj: object to deserialize
        :type obj: dict
        :param opts: options to change the behaviour of the serialization.
        :type opts: SerializerOpts | None
        :return: deserializes object
        :rtype: ClassNoAnnotation
        """
        return ClassNoAnnotation(obj["value"])


class ClassMismatchType:
    """
    Class that implements serialization logic incorrectly
    """

    def __init__(self, value: int) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.value = value

    def serialize(self, **_kwargs: Any) -> dict[str, int]:
        r"""
        Serialization method

        :param \**_kwargs: optional extra keyword arguments
        :return: serialized object
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(obj: Any, **_kwargs: Any) -> ClassMismatchType:
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

    def serialize(
        self,
        opts: SerializerOpts,
    ) -> dict[str, int]:
        """
        Serialization method

        :param opts: options to change the behaviour of the serialization.
        :return: serialized object
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(
        obj: dict[str, int],
        opts: DeserializerOpts,
    ) -> ClassCorrect:
        """
        Deserialization method

        :param obj: object to deserialize
        :param opts: options to change the behaviour of the serialization.
        :return: deserializes object
        """
        return ClassCorrect(obj["value"])

    def __eq__(self, other: object) -> bool:
        """
        Equality.

        :param other: Instance to compare to.
        """
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value == other.value


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

    def serialize(self, opts: SerializerOpts) -> dict[str, int]:
        """
        Serialization method

        :param opts: options to change the behaviour of the serialization.
        :return: serialized object
        """
        return {"value": self.value}

    @staticmethod
    def deserialize(obj: dict[str, int], opts: DeserializerOpts) -> ClassCorrect2:
        """
        Deserialization method

        :param obj: object to deserialize
        :param opts: options to change the behaviour of the serialization.
        :return: deserializes object
        """
        return ClassCorrect2(obj["value"])

    def __eq__(self, other: object) -> bool:
        """
        Equality.

        :param other: Instance to compare to.
        """
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value == other.value


class ClassCorrect3:
    """
    Class that implements serialization logic correctly
    """

    def __init__(self, values: list[int], name: str) -> None:
        """
        Initialization of class

        :param values: list of values; values attribute of class
        :param name: name attribute of class
        """
        self.values = values
        self.name = name

    def serialize(
        self,
        opts: SerializerOpts,
    ) -> bytes:
        """
        Serialization method

        :param opts: options to change the behaviour of the serialization.
        :return: serialized object
        """
        return Serializer.serialize(
            {
                "values": self.values,
                "name": self.name,
            },
            opts,
        )

    @staticmethod
    def deserialize(
        obj: bytes,
        opts: DeserializerOpts,
    ) -> ClassCorrect3:
        """
        Deserialization method

        :param obj: object to deserialize
        :param opts: options to change the behaviour of the serialization.
        :return: deserializes object
        """
        dict_obj = Serializer.deserialize(obj, opts)
        return ClassCorrect3(dict_obj["values"], dict_obj["name"])

    def __eq__(self, other: object) -> bool:
        """
        Equality.

        :param other: Instance to compare to.
        """
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.values == other.values and self.name == other.name


class ClassNoKwargs:
    """
    Class that implements correct serialization logic but doesn't use optional keyword arguments.
    """

    def __init__(self, values: list[int], name: str) -> None:
        """
        Initialization of class

        :param values: list of values; values attribute of class
        :param name: name attribute of class
        """
        self.values = values
        self.name = name

    def serialize(self) -> dict[str, Any]:
        """
        Serialization method

        :return: serialized object
        """
        return {
            "values": self.values,
            "name": self.name,
        }

    @staticmethod
    def deserialize(obj: dict[str, Any]) -> ClassNoKwargs:
        """
        Deserialization method

        :param obj: object to deserialize
        :return: deserializes object
        """
        return ClassNoKwargs(obj["values"], obj["name"])


class NestedClassCorrect(SupportsSerialization):
    """
    Class that implements serialization logic correctly
    """

    def __init__(self, instance: ClassCorrect, dataclass: MyDataClass) -> None:
        """
        Initialization of class

        :param value: value attribute of class
        """
        self.instance = instance
        self.dataclass = dataclass

    def serialize(self, opts: SerializerOpts) -> dict[str, Any]:
        """
        Serialization method

        :param opts: options to change the behaviour of the serialization.
        :return: serialized object
        """
        return {"instance": self.instance, "dataclass": self.dataclass}

    @staticmethod
    def deserialize(
        obj: dict[str, Any],
        opts: DeserializerOpts,
    ) -> NestedClassCorrect:
        """
        Deserialization method

        :param obj: object to deserialize
        :param opts: options to change the behaviour of the serialization.
        :return: deserializes object
        """
        return NestedClassCorrect(**obj)

    def __eq__(self, other: object) -> bool:
        """
        Equality.

        :param other: Instance to compare to.
        """
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.instance == other.instance and self.dataclass == other.dataclass


@dataclass(eq=True)
class MyDataClass:
    """
    Dataclass with custom serialization logic
    """

    attribute: int

    def serialize(
        self,
        opts: SerializerOpts,
    ) -> dict[str, int]:
        r"""
        Serialization method

        :param opts: options to change the behaviour of the serialization.
        :return: serialized object
        """
        return asdict(self)

    @staticmethod
    def deserialize(
        obj: dict[str, int],
        opts: DeserializerOpts,
    ) -> MyDataClass:
        """
        Deserialization method

        :param obj: object to deserialize
        :param opts: options to change the behaviour of the serialization.
        :return: deserialized object
        """
        return MyDataClass(**obj)


@pytest.mark.parametrize("correct_class", (ClassCorrect, ClassCorrect2))
def test_custom_serialization_correct(
    correct_class: type[ClassCorrect | ClassCorrect2],
) -> None:
    """
    Tests correctly implemented serialization logic

    :param correct_class: a correctly implemented serialization class
    """
    Serializer.clear_serialization_logic()
    Serializer.register_class(correct_class)
    obj = correct_class(1)
    pack_unpack_test(obj)


@pytest.mark.parametrize(
    "correct_class, correct_class_2",
    (
        (ClassCorrect2, ClassCorrect3),
        (ClassCorrect, ClassCorrect3),
    ),
)
def test_custom_serialization_correct2(
    correct_class: type[ClassCorrect | ClassCorrect2],
    correct_class_2: type[ClassCorrect3],
) -> None:
    """
    Tests correctly implemented serialization logic

    :param correct_class: a correctly implemented serialization class
    :param correct_class_2: a correctly implemented serialization class
    """
    Serializer.clear_serialization_logic()
    Serializer.register_class(correct_class)
    Serializer.register_class(correct_class_2)
    obj = correct_class(1)
    pack_unpack_test(obj)
    obj2 = correct_class_2([1, 2, 3, 4], "test")
    pack_unpack_test(obj2)


def test_dataclass_serialization() -> None:
    """
    Tests packing and unpacking of dataclasses with custom serialization logic
    """
    Serializer.clear_serialization_logic()
    Serializer.register_class(MyDataClass)
    my_dataclass = MyDataClass(1)

    pack_unpack_test(my_dataclass)


def test_typeddict_serialization() -> None:
    """
    Tests packing and unpacking of dataclasses with custom serialization logic
    """
    Serializer.clear_serialization_logic()
    Serializer.register_class(MyDataClass)
    my_dataclass = MyDataClass(1)

    pack_unpack_test(my_dataclass)


def test_ndarray_custom_logic_elements_serialization() -> None:
    """
    Tests packing and unpacking of a numpy array with custom-serialized elements
    """
    Serializer.clear_serialization_logic()
    array_: npt.NDArray[np.int_] = np.array([ClassCorrect(1)])

    with pytest.raises(
        TypeError, match="Type is not msgpack serializable: ClassCorrect"
    ):
        pack_unpack_test(
            array_,
            serial_option=ormsgpack.OPT_SERIALIZE_NUMPY,
            fallback_pickle=False,
        )

    Serializer.register_class(ClassCorrect)
    pack_unpack_test(
        array_,
        comparator=np.array_equal,
        serial_option=ormsgpack.OPT_SERIALIZE_NUMPY,
        fallback_pickle=False,
    )


def test_series_custom_logic_elements_serialization() -> None:
    """
    Tests packing and unpacking of a pandas series with custom-serialized elements
    """
    Serializer.clear_serialization_logic()
    Serializer.register_class(ClassCorrect)
    series = pd.Series([ClassCorrect(1)])

    pack_unpack_test(
        series,
        comparator=lambda df1, df2: df1.equals(df2),
        fallback_pickle=False,
    )


def test_dataframe_custom_logic_elements_serialization() -> None:
    """
    Tests packing and unpacking of a pandas dataframe with custom-serialized elements
    """
    Serializer.clear_serialization_logic()
    Serializer.register_class(ClassCorrect)
    dataframe = pd.DataFrame({"col1": [ClassCorrect(1)]})

    pack_unpack_test(
        dataframe,
        comparator=lambda df1, df2: df1.equals(df2),
        fallback_pickle=False,
    )


def test_series_nested_custom_logic_elements_serialization() -> None:
    """
    Tests packing and unpacking of a pandas series with nested custom-serialized elements
    """
    Serializer.clear_serialization_logic()
    Serializer.register_class(ClassCorrect)
    Serializer.register_class(MyDataClass)
    Serializer.register_class(NestedClassCorrect)
    series = pd.Series([NestedClassCorrect(ClassCorrect(1), MyDataClass(1))])

    pack_unpack_test(
        series,
        comparator=lambda df1, df2: df1.equals(df2),
        fallback_pickle=False,
    )


def test_dataframe_nested_custom_logic_elements_serialization() -> None:
    """
    Tests packing and unpacking of a pandas dataframe with nested custom-serialized elements
    """
    Serializer.clear_serialization_logic()
    Serializer.register_class(ClassCorrect)
    Serializer.register_class(MyDataClass)
    Serializer.register_class(NestedClassCorrect)
    dataframe = pd.DataFrame(
        {"col1": [NestedClassCorrect(ClassCorrect(1), MyDataClass(1))]}
    )

    pack_unpack_test(
        dataframe,
        comparator=lambda df1, df2: df1.equals(df2),
        fallback_pickle=False,
    )
