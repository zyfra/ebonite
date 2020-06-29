from ebonite.core.analyzer.dataset import DatasetAnalyzer, DatasetHook
from ebonite.core.objects import DatasetType


class MyDataset:
    pass


class MyDatasetType(DatasetType):
    pass


class MyDatasetHook(DatasetHook):

    def process(self, obj, **kwargs) -> DatasetType:
        return MyDatasetType()

    def can_process(self, obj) -> bool:
        return isinstance(obj, MyDataset)

    def must_process(self, obj) -> bool:
        return self.can_process(obj)


def test_dataset_analyzer():
    data = MyDataset()

    data_type = DatasetAnalyzer.analyze(data)

    assert issubclass(data_type, MyDatasetType)
