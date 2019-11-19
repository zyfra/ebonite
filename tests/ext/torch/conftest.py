import pytest


@pytest.fixture
def first_tensor():
    import torch
    return torch.rand(5, 10)


@pytest.fixture
def second_tensor():
    import torch
    return torch.rand(5, 5)
