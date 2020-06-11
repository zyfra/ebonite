from abc import abstractmethod


class DatasetRepository:
    @abstractmethod
    def save(self, datset):
        pass
