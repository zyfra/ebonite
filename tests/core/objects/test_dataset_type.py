import numpy as np
import pytest
from pyjackson import deserialize, serialize
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import (DatasetType, DictDatasetType, ListDatasetType, PrimitiveDatasetType,
                                               TupleDatasetType, TupleLikeListDatasetType)


class DTHolder:
    def __init__(self, dt: DatasetType):
        self.dt = dt


@pytest.fixture
def dt():
    return PrimitiveDatasetType('int')


def test_primitive_dataset_type_serialize(dt):
    assert serialize(123, dt) == 123
    with pytest.raises(SerializationError):
        dt.serialize('abc')


def test_primitive_dataset_type_deserialize(dt):
    assert deserialize(123, dt)
    with pytest.raises(DeserializationError):
        assert dt.deserialize('abc')


def test_primitive_dataset_type(dt):
    assert dt == PrimitiveDatasetType('int')

    payload = serialize(dt)

    assert payload == {'type': 'primitive', 'ptype': 'int'}


def test_inner_primitive_dataset_type(dt):
    dth = DTHolder(dt)

    payload = serialize(dth)

    assert payload == {'dt': {'type': 'primitive', 'ptype': 'int'}}


def test_primitive_type_requirements(dt):
    assert dt.requirements.modules == []


@pytest.fixture
def tlldt():
    return DatasetAnalyzer.analyze(['a', 1])


def test_tuple_like_list_dataset_type_serialize(tlldt):
    assert serialize(['b', 2], tlldt) == ['b', 2]
    with pytest.raises(SerializationError):
        tlldt.serialize('abc')


def test_tuple_like_list_dataset_type_deserialize(tlldt):
    assert deserialize(['c', 3], tlldt) == ['c', 3]
    with pytest.raises(DeserializationError):
        assert tlldt.deserialize('abc')


def test_tuple_like_list_dataset_type(tlldt):
    assert tlldt == TupleLikeListDatasetType([PrimitiveDatasetType('str'), PrimitiveDatasetType('int')])

    payload = serialize(tlldt)

    assert payload == {'type': 'tuple_like_list',
                       'items': [{'type': 'primitive', 'ptype': 'str'}, {'type': 'primitive', 'ptype': 'int'}]}


def test_inner_tuple_like_list_dataset_type(tlldt):
    dth = DTHolder(tlldt)

    payload = serialize(dth)

    assert payload == {'dt': {'type': 'tuple_like_list',
                              'items': [{'type': 'primitive', 'ptype': 'str'}, {'type': 'primitive', 'ptype': 'int'}]}}


def test_tuple_like_list_type_requirements():
    tlldt = DatasetAnalyzer.analyze(['a', 1, np.float32(4.2)])
    assert tlldt.requirements.modules == ['numpy']


@pytest.fixture
def tdt():
    return DatasetAnalyzer.analyze(('a', 1))


def test_tuple_dataset_type_serialize(tdt):
    assert serialize(('b', 2), tdt) == ('b', 2)
    with pytest.raises(SerializationError):
        tdt.serialize('abc')


def test_tuple_dataset_type_deserialize(tdt):
    assert deserialize(('c', 3), tdt) == ('c', 3)
    with pytest.raises(DeserializationError):
        assert tdt.deserialize('abc')


def test_tuple_dataset_type(tdt):
    assert tdt == TupleDatasetType([PrimitiveDatasetType('str'), PrimitiveDatasetType('int')])

    payload = serialize(tdt)

    assert payload == {'type': 'tuple',
                       'items': [{'type': 'primitive', 'ptype': 'str'}, {'type': 'primitive', 'ptype': 'int'}]}


def test_inner_tuple_dataset_type(tdt):
    dth = DTHolder(tdt)

    payload = serialize(dth)

    assert payload == {'dt': {'type': 'tuple',
                              'items': [{'type': 'primitive', 'ptype': 'str'}, {'type': 'primitive', 'ptype': 'int'}]}}


def test_tuple_type_requirements():
    tlldt = DatasetAnalyzer.analyze(('a', 1, np.float32(4.2)))
    assert tlldt.requirements.modules == ['numpy']


@pytest.fixture
def ldt():
    return DatasetAnalyzer.analyze([1, 1])


def test_list_dataset_type_serialize(ldt):
    assert serialize([2, 2], ldt) == [2, 2]
    with pytest.raises(SerializationError):
        ldt.serialize('abc')


def test_list_dataset_type_deserialize(ldt):
    assert deserialize([3, 3], ldt) == [3, 3]
    with pytest.raises(DeserializationError):
        assert ldt.deserialize('abc')


def test_list_dataset_type(ldt):
    assert ldt == ListDatasetType(PrimitiveDatasetType('int'), 2)

    payload = serialize(ldt)

    assert payload == {'type': 'list',
                       'dtype': {'type': 'primitive', 'ptype': 'int'},
                       'size': 2}


def test_inner_list_dataset_type(ldt):
    dth = DTHolder(ldt)

    payload = serialize(dth)

    assert payload == {'dt': {'type': 'list',
                              'dtype': {'type': 'primitive', 'ptype': 'int'},
                              'size': 2}}


def test_list_type_requirements():
    tlldt = DatasetAnalyzer.analyze([np.float32(7.3), np.float32(4.2)])
    assert tlldt.requirements.modules == ['numpy']


@pytest.fixture
def ddt():
    return DatasetAnalyzer.analyze({'a': 1})


def test_dict_dataset_type_serialize(ddt):
    assert serialize({'a': 2}, ddt) == {'a': 2}
    with pytest.raises(SerializationError):
        ddt.serialize('abc')


def test_dict_dataset_type_deserialize(ddt):
    assert deserialize({'a': 3}, ddt) == {'a': 3}
    with pytest.raises(DeserializationError):
        assert ddt.deserialize('abc')


def test_dict_dataset_type(ddt):
    assert ddt == DictDatasetType({'a': PrimitiveDatasetType('int')})

    payload = serialize(ddt)

    assert payload == {'type': 'dict',
                       'item_types': {"a": {'type': 'primitive', 'ptype': 'int'}}}


def test_inner_dict_dataset_type(ddt):
    dth = DTHolder(ddt)

    payload = serialize(dth)

    assert payload == {'dt': {'type': 'dict',
                              'item_types': {"a": {'type': 'primitive', 'ptype': 'int'}}}}


def test_dict_with_list_dataset_type():
    data = {'a': ['b']}
    dt = DatasetAnalyzer.analyze(data)

    assert dt == DictDatasetType({'a': TupleLikeListDatasetType([PrimitiveDatasetType('str')])})

    assert serialize(data, dt) == data
    assert deserialize(data, dt) == data

    with pytest.raises(DeserializationError):
        deserialize('', dt)

    with pytest.raises(SerializationError):
        serialize('', dt)

    payload = serialize(dt)
    assert payload == {'type': 'dict',
                       'item_types': {
                           'a': {'type': 'tuple_like_list',
                                 'items': [{'type': 'primitive', 'ptype': 'str'}]}
                       }}

    payload = serialize(DTHolder(dt))
    assert payload == {'dt': {'type': 'dict',
                              'item_types': {
                                  'a': {'type': 'tuple_like_list',
                                        'items': [{'type': 'primitive', 'ptype': 'str'}]}
                              }}
                       }


def test_dict_type_requirements():
    tlldt = DatasetAnalyzer.analyze({'a': 10, 'b': np.float32(4.2)})
    assert tlldt.requirements.modules == ['numpy']


def test_bytes_type():
    b = b'hello'
    bdt = DatasetAnalyzer.analyze(b)

    assert bdt.serialize(b) == b
    assert bdt.deserialize(b) == b
    assert bdt.requirements.modules == []
