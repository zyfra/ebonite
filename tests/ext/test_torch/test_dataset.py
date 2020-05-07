import pytest
import torch
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.runtime.openapi.spec import type_to_schema


@pytest.fixture
def tdt_list(first_tensor, second_tensor):
    # this import ensures that this dataset type is registered in `DatasetAnalyzer`
    from ebonite.ext.torch.dataset import TorchTensorDatasetType  # noqa

    tensor_list = [first_tensor, second_tensor]
    return DatasetAnalyzer.analyze(tensor_list)


def test_torch__single_tensor(first_tensor):
    # this import ensures that this dataset type is registered in `DatasetAnalyzer`
    from ebonite.ext.torch.dataset import TorchTensorDatasetType  # noqa

    tdt = DatasetAnalyzer.analyze(first_tensor)

    assert tdt.requirements.modules == ['torch']
    assert tdt.shape == (None, 5)
    assert tdt.dtype == 'int32'
    assert type_to_schema(tdt) == {
        'items': {
            'items': {'type': 'integer'},
            'maxItems': 5,
            'minItems': 5,
            'type': 'array'
        },
        'type': 'array'
    }

    tensor_deser = tdt.deserialize(tdt.serialize(first_tensor))
    assert torch.equal(first_tensor, tensor_deser)
    assert first_tensor.dtype == tensor_deser.dtype


def test_torch__tensors_list(tdt_list, first_tensor, second_tensor):
    assert tdt_list.requirements.modules == ['torch']
    assert len(tdt_list.items) == 2
    assert tdt_list.items[0].shape == (None, 5)
    assert tdt_list.items[0].dtype == 'int32'
    assert tdt_list.items[1].shape == (None, 10)
    assert tdt_list.items[1].dtype == 'float32'
    assert type_to_schema(tdt_list) == {
        'properties': {
            '0': {
                'items': {
                    'items': {'type': 'integer'},
                    'maxItems': 5,
                    'minItems': 5,
                    'type': 'array'
                },
                'type': 'array'
            },
            '1': {
                'items': {
                    'items': {'type': 'number'},
                    'maxItems': 10,
                    'minItems': 10,
                    'type': 'array'
                },
                'type': 'array'
            }
        },
        'required': ['0', '1'],
        'type': 'object'
    }

    tensor_list = [first_tensor, second_tensor]
    tensor_list_deser = tdt_list.deserialize(tdt_list.serialize(tensor_list))
    assert len(tensor_list) == len(tensor_list_deser)
    assert all(torch.equal(tensor, tensor_deser) and tensor.dtype == tensor_deser.dtype
               for tensor, tensor_deser in zip(tensor_list, tensor_list_deser))


def test_torch__serialize_failure(tdt_list, first_tensor, second_tensor):
    objs = [
        first_tensor,                         # not a list
        [first_tensor, second_tensor] * 2,    # not a list of 2
        [first_tensor] * 2,                   # wrong dtype for second
        [first_tensor, first_tensor.float()]  # wrong shape for second
    ]

    for obj in objs:
        with pytest.raises(SerializationError):
            tdt_list.serialize(obj)


@pytest.mark.parametrize('obj', [
    [[[1, 2], [3]], [[1], [2]]],  # illegal tensor for first
    [[[1, 2]], []]                # wrong shapes for both
])
def test_torch__deserialize_failure(tdt_list, obj):
    with pytest.raises(DeserializationError):
        tdt_list.deserialize(obj)
