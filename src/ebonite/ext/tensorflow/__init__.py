# EBNT-142 too many Tensorflow deprecation warnings
def fix_warnings():  # noqa
    import logging  # noqa
    import warnings  # noqa
    logging.getLogger("tensorflow").setLevel(logging.CRITICAL)  # noqa
    warnings.filterwarnings('ignore', category=FutureWarning)  # noqa
    warnings.filterwarnings('ignore', category=DeprecationWarning)  # noqa
fix_warnings()  # noqa


from .dataset import FeedDictDatasetType, FeedDictHook
from .model import TFTensorHook, TFTensorModelWrapper

__all__ = ['FeedDictHook', 'FeedDictDatasetType', 'TFTensorHook', 'TFTensorModelWrapper']
