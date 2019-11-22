import pytest
import torch


@pytest.fixture
def first_tensor():
    return torch.ones(5, 5, dtype=torch.int32)


@pytest.fixture
def second_tensor():
    return torch.rand(5, 10, dtype=torch.float32)
