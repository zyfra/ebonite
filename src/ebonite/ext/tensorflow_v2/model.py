import contextlib
import os
import shutil
import tempfile
from typing import Dict

import tensorflow as tf
from pyjackson.decorators import make_string

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects import ModelIO, ModelWrapper
from ebonite.core.objects.artifacts import Blobs, LocalFileBlob
from ebonite.core.objects.wrapper import FilesContextManager


class TFKerasModelIO(ModelIO):
    """
    :class:`.ModelIO` implementation for Tensorflow Keras models (:class:`tensorflow.keras.Model` objects)
    """

    model_dir_name = 'model.tf'
    ext = '.zip'

    @contextlib.contextmanager
    def dump(self, model) -> FilesContextManager:
        with tempfile.TemporaryDirectory(prefix='ebonite_tf_v2') as tmpdir:
            dir_path = os.path.join(tmpdir, self.model_dir_name)

            model.save(dir_path)
            shutil.make_archive(dir_path, 'zip', dir_path)

            yield Blobs({self.model_dir_name + self.ext: LocalFileBlob(dir_path + self.ext)})

    def load(self, path):
        file_path = os.path.join(path, self.model_dir_name + self.ext)

        with tempfile.TemporaryDirectory(prefix='ebonite_tf_v2') as tmpdir:
            shutil.unpack_archive(file_path, tmpdir)
            return tf.keras.models.load_model(tmpdir)


class TFKerasModelWrapper(ModelWrapper):
    """
    :class:`.ModelWrapper` implementation for Tensorflow Keras models (:class:`tensorflow.keras.Model` objects)
    """
    def __init__(self):
        super().__init__(TFKerasModelIO())

    def _exposed_methods_mapping(self) -> Dict[str, str]:
        return {
            'predict': 'predict'
        }


@make_string(include_name=True)
class TFKerasModelHook(BindingModelHook, TypeHookMixin):
    """
    Hook for Tensorflow Keras models
    """
    valid_types = [tf.keras.Model]

    def _wrapper_factory(self) -> ModelWrapper:
        """
        Creates :class:`.TFKerasModelWrapper` for Tensorflow Keras model object

        :return: :class:`.TFKerasModelWrapper` instance
        """
        return TFKerasModelWrapper()
