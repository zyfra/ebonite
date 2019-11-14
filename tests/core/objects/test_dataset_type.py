from pyjackson import serialize

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import DatasetType, PrimitiveDatasetType


class DTHolder:
    def __init__(self, dt: DatasetType):
        self.dt = dt


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
