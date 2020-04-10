import pytest
import torch

from ebonite.core.analyzer.model import ModelAnalyzer


class MyNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = [torch.nn.Linear(5, 1), torch.nn.Linear(10, 1)]

    def forward(self, *inputs):
        results = torch.cat([layer(input) for layer, input in zip(self.layers, inputs)], dim=1)
        return results.sum(dim=1)


@pytest.mark.parametrize('net', [
    torch.nn.Linear(5, 1),
    torch.jit.script(torch.nn.Linear(5, 1))
])
def test_torch__builtin_net(net, first_tensor, tmpdir):
    _check_model_wrapper(net, first_tensor.float(), tmpdir)


def test_torch__custom_net(first_tensor, second_tensor, tmpdir):
    _check_model_wrapper(MyNet(), [first_tensor.float(), second_tensor], tmpdir)


def _check_model_wrapper(net, input_data, tmpdir):
    # this import is required for dataset type to be registered
    import ebonite.ext.torch  # noqa

    tmw = ModelAnalyzer.analyze(net, input_data=input_data)

    assert tmw.model is net

    expected_requirements = {'torch'}
    assert set(tmw.requirements.modules) == expected_requirements

    prediction = tmw.call_method('predict', input_data)

    with tmw.dump() as artifact:
        artifact.materialize(tmpdir)

    tmw.unbind()
    with pytest.raises(ValueError):
        tmw.call_method('predict', input_data)

    tmw.load(tmpdir)

    assert tmw.model is not net

    prediction2 = tmw.call_method('predict', input_data)

    assert torch.equal(prediction, prediction2)

    assert set(tmw.requirements.modules) == expected_requirements
