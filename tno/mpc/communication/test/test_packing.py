import tno.mpc.communication.communication as communication
from numpy import array, array_equal
import pytest
import copy
import typing


def pack_unpack_test(obj, eq=lambda a, b: a == b, expect=True):
    msg_id = "test_id"
    Com = communication.Communication
    obj_copy = copy.deepcopy(obj)
    msg_id_prime, obj_prime = Com.unpack(Com.pack(obj, msg_id))
    obj = obj_copy
    if expect:
        assert eq(obj, obj_prime) and msg_id == msg_id_prime
    else:
        assert (not eq(obj, obj_prime)) and msg_id == msg_id_prime


def test_int_serialization():
    pack_unpack_test(1)


def test_float_serialization():
    pack_unpack_test(1.0)


def test_str_serialization():
    pack_unpack_test("test string")


def test_bytes_serialization():
    pack_unpack_test(b"10101")


def test_empty_list():
    list_ = []
    pack_unpack_test(list_)


def test_list_serialization_same_type():
    list_ = [1, 2, 3, 4, 5]
    pack_unpack_test(list_)


def test_list_serialization_dif_type():
    list_ = [1, 2.0, "3", [4]]
    pack_unpack_test(list_)


def test_empty_tuple():
    tuple_ = ()
    pack_unpack_test(tuple_)


def test_tuple_serialization_same_type():
    tuple_ = (1, 2, 3, 4, 5)
    pack_unpack_test(tuple_)


def test_tuple_serialization_dif_type():
    tuple_ = (1, 2.0, "3", [4], (5,))
    pack_unpack_test(tuple_)


def test_dict_serialization():
    d = {"1": 1, "2": 2}
    pack_unpack_test(d)


def test_monstrous_collection_serialization():
    c = [
        [[1, 2], [3, 4], "5", 6],
        "7",
        "z",
        {"8": 9, 10: "11", 12.1: 13.2},
        {"14": 15, 16: "17", 18.1: 19.2},
        [[[20], "21", 22.1], "13"],
        ([1, 2], "3", 3.0, {"4": 5.0}, (6, 7)),
    ]
    pack_unpack_test(c)


def test_ndarray_serialization():
    array_ = array([1, 2, 3, 4, 5])
    pack_unpack_test(array_, lambda a, b: array_equal(a, b))


def eq_encrypted_number(enc1, enc2):
    return (
        enc1.exponent == enc2.exponent
        and enc1.ciphertext(False) == enc2.ciphertext(False)
        and enc1.public_key.n == enc2.public_key.n
    )


def test_custom_serialization_no_logic():
    communication.Communication.clear_new_serialization_logic()
    with pytest.raises(AttributeError):
        communication.Communication.set_serialization_logic(ClassNoLogic)


def test_custom_serialization_no_functions():
    communication.Communication.clear_new_serialization_logic()
    with pytest.raises(TypeError):
        communication.Communication.set_serialization_logic(ClassNoFunctions)


def test_custom_serialization_wrong_annotation():
    communication.Communication.clear_new_serialization_logic()
    with pytest.raises(communication.AnnotationError):
        communication.Communication.set_serialization_logic(ClassWrongAnnotation)


def test_custom_serialization_no_annotation():
    communication.Communication.clear_new_serialization_logic()
    with pytest.raises(communication.AnnotationError):
        communication.Communication.set_serialization_logic(ClassNoAnnotation)


def test_custom_serialization_correct():
    communication.Communication.clear_new_serialization_logic()
    communication.Communication.set_serialization_logic(ClassCorrect)
    obj = ClassCorrect(1)
    pack_unpack_test(obj, lambda a, b: a.value == b.value)


def test_custom_serialization_correct_double():
    communication.Communication.clear_new_serialization_logic()
    with pytest.raises(communication.RepetitionError):
        communication.Communication.set_serialization_logic(ClassCorrect)
        # setting logic twice makes no sense. This should return a RepetitionError
        communication.Communication.set_serialization_logic(ClassCorrect)
        obj = ClassCorrect(1)
        pack_unpack_test(obj, lambda a, b: a.value == b.value)


def test_custom_serialization_correct2():
    communication.Communication.clear_new_serialization_logic()
    communication.Communication.set_serialization_logic(ClassCorrect)
    communication.Communication.set_serialization_logic(ClassCorrect2)
    obj = ClassCorrect(1)
    pack_unpack_test(obj, lambda a, b: a.value == b.value)
    obj2 = ClassCorrect2([1, 2, 3, 4], "test")
    pack_unpack_test(obj2, lambda a, b: a.values == b.values and a.name == b.name)


class ClassNoLogic:
    def __init__(self, value: int):
        self.value = value


class ClassNoFunctions:

    serialize = 0
    deserialize = 0

    def __init__(self, value: int):
        self.value = value


class ClassWrongAnnotation:
    def __init__(self, value: int):
        self.value = value

    def serialize(self) -> int:
        return self.value

    @staticmethod
    def deserialize(value) -> "ClassWrongAnnotation":
        return ClassWrongAnnotation(value)


class ClassNoAnnotation:
    def __init__(self, value: int):
        self.value = value

    def serialize(self):
        return {"value": self.value}

    @staticmethod
    def deserialize(json):
        return ClassCorrect(json["value"])


class ClassCorrect:
    def __init__(self, value: int):
        self.value = value

    def serialize(self) -> dict:
        return {"value": self.value}

    @staticmethod
    def deserialize(json: dict) -> "ClassCorrect":
        return ClassCorrect(json["value"])


class ClassCorrect2:
    def __init__(self, values: typing.List[int], name: str):
        self.values = values
        self.name = name

    def serialize(self) -> dict:
        return {
            "values": communication.Communication.serialize(self.values),
            "name": communication.Communication.serialize(self.name),
        }

    @staticmethod
    def deserialize(json: dict) -> "ClassCorrect2":
        return ClassCorrect2(
            communication.Communication.deserialize(json["values"]),
            communication.Communication.deserialize(json["name"]),
        )
