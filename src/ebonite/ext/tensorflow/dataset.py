from typing import Mapping

import tensorflow as tf
from pyjackson import serialize

from ebonite.core.analyzer.base import CanIsAMustHookMixin
from ebonite.core.analyzer.dataset import DatasetAnalyzer, DatasetHook
from ebonite.core.objects.dataset_type import DatasetType, DictDatasetType


class FeedDictDatasetType(DictDatasetType):
    """
    :class:`~ebonite.core.objects.DatasetType` implementation for tensorflow feed dict argument
    """
    type = 'tf_feed_dict'

    @classmethod
    def from_feed_dict(cls, feed_dict):
        """
        Factory method to create :class:`FeedDictDatasetType` from feed dict

        :param feed_dict: feed dict
        :return: :class:`FeedDictDatasetType` instance
        """
        types = {}
        for k, v in feed_dict.items():
            types[cls.get_key(k)] = DatasetAnalyzer.analyze(v)
        return FeedDictDatasetType(types)

    def serialize(self, instance: dict):
        items = ((self.get_key(k), v) for k, v in instance.items())
        return {k: serialize(v, self.item_types[k]) for k, v in items}

    @staticmethod
    def get_key(k):
        if isinstance(k, tf.Tensor):
            return k.name
        elif isinstance(k, str):
            return k
        else:
            raise ValueError(f'Unknown key type {type(k).__name__} for key {k} in feed_dict')


class FeedDictHook(CanIsAMustHookMixin, DatasetHook):
    """
    DatasetHook for tensorflow feed dict
    """

    def must_process(self, obj) -> bool:
        """
        :param obj: obj to check
        :return: `True` if obj is mapping and any of it's keys are tf.Tensor instance
        """
        is_mapping = isinstance(obj, Mapping)
        return is_mapping and any(isinstance(k, tf.Tensor) for k in obj.keys())

    def process(self, obj) -> DatasetType:
        """
        :param obj: obj to process
        :return: :class:`FeedDictDatasetType` instance
        """
        return FeedDictDatasetType.from_feed_dict(obj)
