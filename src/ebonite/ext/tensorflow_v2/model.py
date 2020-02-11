import contextlib
import os
import shutil
import tempfile
from typing import Dict

import tensorflow as tf
from pyjackson.decorators import make_string

from ebonite.core.analyzer import CanIsAMustHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects import ModelWrapper
from ebonite.core.objects.artifacts import Blobs, LocalFileBlob
from ebonite.core.objects.wrapper import FilesContextManager


class TFKerasModelWrapper(ModelWrapper):
    """
    :class:`.ModelWrapper` implementation for Tensorflow Keras models (:class:`tensorflow.keras.Model` objects)
    """

    model_dir_name = 'model.tf'
    ext = '.zip'

    @ModelWrapper.with_model
    @contextlib.contextmanager
    def _dump(self) -> FilesContextManager:
        with tempfile.TemporaryDirectory(prefix='ebonite_tf_v2') as tmpdir:
            dir_path = os.path.join(tmpdir, self.model_dir_name)

            self.model.save(dir_path)
            shutil.make_archive(dir_path, 'zip', dir_path)

            yield Blobs({self.model_dir_name + self.ext: LocalFileBlob(dir_path + self.ext)})

    def _load(self, path):
        file_path = os.path.join(path, self.model_dir_name + self.ext)

        with tempfile.TemporaryDirectory(prefix='ebonite_tf_v2') as tmpdir:
            shutil.unpack_archive(file_path, tmpdir)
            self.model = tf.keras.models.load_model(tmpdir)

    def _exposed_methods_mapping(self) -> Dict[str, str]:
        return {
            'predict': 'predict'
        }


@make_string(include_name=True)
class TFKerasModelHook(ModelHook, CanIsAMustHookMixin):
    """
    Hook for Tensorflow Keras models
    """

    def must_process(self, obj) -> bool:
        """
        Returns `True` if object is :class:`tensorflow.keras.Model`

        :param obj: obj to check
        :return: `True` or `False`
        """
        return isinstance(obj, tf.keras.Model)

    def process(self, obj, **kwargs) -> ModelWrapper:
        """
        Creates :class:`.TFKerasModelWrapper` for Tensorflow Keras model object

        :param obj: obj to process
        :param kwargs: additional information to be used for analysis
        :return: :class:`.TFKerasModelWrapper` instance
        """
        return TFKerasModelWrapper().bind_model(obj, **kwargs)
