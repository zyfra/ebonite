import torch

from ebonite.core.analyzer.model import ModelAnalyzer


class MyNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = [torch.nn.Linear(5, 1), torch.nn.Linear(10, 1)]

    def forward(self, *inputs):
        results = torch.cat([layer(input) for layer, input in zip(self.layers, inputs)], dim=1)
        return results.sum(dim=1)


def test_torch__builtin_net(first_tensor, tmpdir):
    input_data = first_tensor.float()
    net = torch.nn.Linear(5, 1)
    net2 = _check_model_wrapper(net, input_data, tmpdir)
    assert torch.equal(net(input_data), net2(input_data))


def test_torch__custom_net(first_tensor, second_tensor, tmpdir):
    input_data = [first_tensor.float(), second_tensor]
    net = MyNet()
    net2 = _check_model_wrapper(net, input_data, tmpdir)
    assert torch.equal(net(*input_data), net2(*input_data))


def _check_model_wrapper(net, input_data, tmpdir):
    # this import is required for dataset type to be registered
    import ebonite.ext.torch  # noqa

    tmw = ModelAnalyzer.analyze(net, input_data=input_data)

    assert tmw.model is net

    with tmw.dump() as artifact:
        artifact.materialize(tmpdir)
    tmw.load(tmpdir)

    assert tmw.model is not net

    return tmw.model
