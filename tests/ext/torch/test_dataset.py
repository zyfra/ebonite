import pytest

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.utils.importing import module_importable


@pytest.mark.skipif(not module_importable('torch'), reason='PyTorch is not installed')
def test_torch__no_hook_no_dataset_types(first_tensor, second_tensor):
    with pytest.raises(ValueError):
        DatasetAnalyzer.analyze(first_tensor)
    with pytest.raises(ValueError):
        DatasetAnalyzer.analyze([first_tensor, second_tensor])


@pytest.mark.skipif(not module_importable('torch'), reason='PyTorch is not installed')
def test_torch__single_tensor(first_tensor):
    import torch

    # this import ensures that this dataset type is registered in `DatasetAnalyzer`
    from ebonite.ext.torch.dataset import TorchTensorDatasetType  # noqa

    tdt = DatasetAnalyzer.analyze(first_tensor)

    assert tdt.shape == (5, 10)
    assert tdt.dtype == 'float32'
    assert tdt.list_size() == 5

    tensor_deser = tdt.deserialize(tdt.serialize(first_tensor))
    assert torch.equal(first_tensor, tensor_deser)


@pytest.mark.skipif(not module_importable('torch'), reason='PyTorch is not installed')
def test_torch__tensors_list(first_tensor, second_tensor):
    import torch

    # this import ensures that this dataset type is registered in `DatasetAnalyzer`
    # from ebonite.ext.torch.dataset import TorchTensorListDatasetType  # noqa

    tensor_list = [first_tensor, second_tensor]
    tdt = DatasetAnalyzer.analyze(tensor_list)

    assert len(tdt.types) == 2
    assert tdt.types[0].shape == (5, 10)
    assert tdt.types[0].dtype == 'float32'
    assert tdt.types[0].list_size() == 5
    assert tdt.types[1].shape == (5, 5)
    assert tdt.types[1].dtype == 'float32'
    assert tdt.types[1].list_size() == 5

    tensor_list_deser = tdt.deserialize(tdt.serialize(tensor_list))
    assert len(tensor_list) == len(tensor_list_deser)
    assert all(torch.equal(tensor, tensor_deser) for tensor, tensor_deser in zip(tensor_list, tensor_list_deser))
