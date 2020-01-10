import pytest
from pyjackson import deserialize, serialize
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import DatasetType, DictDatasetType, ListDatasetType, PrimitiveDatasetType


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


@pytest.fixture
def ldt():
    return DatasetAnalyzer.analyze(['a', 1])


def test_list_dataset_type_serialize(ldt):
    assert serialize(['b', 2], ldt) == ['b', 2]
    with pytest.raises(SerializationError):
        ldt.serialize('abc')


def test_list_dataset_type_deserialize(ldt):
    assert deserialize(['c', 3], ldt) == ['c', 3]
    with pytest.raises(DeserializationError):
        assert ldt.deserialize('abc')


def test_list_dataset_type(ldt):
    assert ldt == ListDatasetType([PrimitiveDatasetType('str'), PrimitiveDatasetType('int')])

    payload = serialize(ldt)

    assert payload == {'type': 'list',
                       'items': [{'type': 'primitive', 'ptype': 'str'}, {'type': 'primitive', 'ptype': 'int'}]}


def test_inner_list_dataset_type(ldt):
    dth = DTHolder(ldt)

    payload = serialize(dth)

    assert payload == {'dt': {'type': 'list',
                              'items': [{'type': 'primitive', 'ptype': 'str'}, {'type': 'primitive', 'ptype': 'int'}]}}


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

    assert dt == DictDatasetType({'a': ListDatasetType([PrimitiveDatasetType('str')])})

    assert serialize(data, dt) == data
    assert deserialize(data, dt) == data

    with pytest.raises(DeserializationError):
        deserialize('', dt)

    with pytest.raises(SerializationError):
        serialize('', dt)

    payload = serialize(dt)
    assert payload == {'type': 'dict',
                       'item_types': {
                           'a': {'type': 'list',
                                 'items': [{'type': 'primitive', 'ptype': 'str'}]}
                       }}

    payload = serialize(DTHolder(dt))
    assert payload == {'dt': {'type': 'dict',
                              'item_types': {
                                  'a': {'type': 'list',
                                        'items': [{'type': 'primitive', 'ptype': 'str'}]}
                              }}
                       }
