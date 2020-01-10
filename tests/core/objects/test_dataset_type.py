import pytest
from pyjackson import serialize
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import DatasetType, PrimitiveDatasetType


class DTHolder:
    def __init__(self, dt: DatasetType):
        self.dt = dt


@pytest.fixture
def dt():
    return PrimitiveDatasetType('int')


def test_primitive_dataset_type_serialize(dt):
    assert dt.serialize(123) == 123
    with pytest.raises(SerializationError):
        dt.serialize('abc')


def test_primitive_dataset_type_deserialize(dt):
    assert dt.deserialize(123) == 123
    with pytest.raises(DeserializationError):
        assert dt.deserialize('abc')


def test_primitive_dataset_type():
    dt = DatasetAnalyzer.analyze('aaa')

    assert dt == PrimitiveDatasetType('str')

    payload = serialize(dt)

    assert payload == {'type': 'primitive', 'ptype': 'str'}


def test_inner_primitive_dataset_type():
    dt = DatasetAnalyzer.analyze('aaa')

    dth = DTHolder(dt)

    payload = serialize(dth)

    assert payload == {'dt': {'type': 'primitive', 'ptype': 'str'}}
