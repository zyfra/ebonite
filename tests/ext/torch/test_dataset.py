import torch

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.runtime.openapi.spec import type_to_schema


def test_torch__single_tensor(first_tensor):
    # this import ensures that this dataset type is registered in `DatasetAnalyzer`
    from ebonite.ext.torch.dataset import TorchTensorDatasetType  # noqa

    tdt = DatasetAnalyzer.analyze(first_tensor)

    assert tdt.shape == (5, 5)
    assert tdt.dtype == 'int32'
    assert tdt.list_size() == 5
    assert type_to_schema(tdt) == {
        'items': {
            'items': {'type': 'integer'},
            'maxItems': 5,
            'minItems': 5,
            'type': 'array'
        },
        'maxItems': 5,
        'minItems': 5,
        'type': 'array'
    }

    tensor_deser = tdt.deserialize(tdt.serialize(first_tensor))
    assert torch.equal(first_tensor, tensor_deser)
    assert first_tensor.dtype == tensor_deser.dtype


def test_torch__tensors_list(first_tensor, second_tensor):
    # this import ensures that this dataset type is registered in `DatasetAnalyzer`
    from ebonite.ext.torch.dataset import TorchTensorDatasetType  # noqa

    tensor_list = [first_tensor, second_tensor]
    tdt = DatasetAnalyzer.analyze(tensor_list)

    assert len(tdt.items) == 2
    assert tdt.items[0].shape == (5, 5)
    assert tdt.items[0].dtype == 'int32'
    assert tdt.items[0].list_size() == 5
    assert tdt.items[1].shape == (5, 10)
    assert tdt.items[1].dtype == 'float32'
    assert tdt.items[1].list_size() == 5
    assert type_to_schema(tdt) == {
        'properties': {
            0: {
                'items': {
                    'items': {'type': 'integer'},
                    'maxItems': 5,
                    'minItems': 5,
                    'type': 'array'
                },
                'maxItems': 5,
                'minItems': 5,
                'type': 'array'
            },
            1: {
                'items': {
                    'items': {'type': 'number'},
                    'maxItems': 10,
                    'minItems': 10,
                    'type': 'array'
                },
                'maxItems': 5,
                'minItems': 5,
                'type': 'array'
            }
        },
        'required': [0, 1],
        'type': 'object'
    }

    tensor_list_deser = tdt.deserialize(tdt.serialize(tensor_list))
    assert len(tensor_list) == len(tensor_list_deser)
    assert all(torch.equal(tensor, tensor_deser) and tensor.dtype == tensor_deser.dtype
               for tensor, tensor_deser in zip(tensor_list, tensor_list_deser))
