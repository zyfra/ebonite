import contextlib
import os
import tempfile
from abc import abstractmethod
from typing import List

import tensorflow as tf
from pyjackson.decorators import make_string
from tensorflow.python.ops import variables

from ebonite.core.analyzer.base import CanIsAMustHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.artifacts import Blobs, LocalFileBlob
from ebonite.core.objects.wrapper import FilesContextManager, ModelWrapper

TF_MODEL_FILENAME = 'graph'


class _TFDump:
    """
    Base class for tf dumping method
    """

    @abstractmethod
    def dump(self, session, path) -> FilesContextManager:
        pass

    @abstractmethod
    def load(self, session, path) -> tf.Graph:
        pass


class _Saver(_TFDump):
    """
    :class:`_TFDump` implementation with tf.train.Saver
    """

    def dump(self, session, path) -> FilesContextManager:
        with session.as_default(), session.graph.as_default():
            saver = tf.train.Saver(save_relative_paths=True)
            saver.save(session, os.path.join(path, TF_MODEL_FILENAME))

        yield Blobs({
            name: LocalFileBlob(os.path.join(path, name)) for name in os.listdir(path)
        })

    def load(self, session, path):
        with session.as_default(), session.graph.as_default():
            saver = tf.train.import_meta_graph(os.path.join(path, TF_MODEL_FILENAME) + '.meta')
            saver.restore(session, os.path.join(path, TF_MODEL_FILENAME))


class _Protobuf(_TFDump):
    """
    :class:`_TFDump` implementation with tf.train.write_graph
    """

    def dump(self, session, path) -> FilesContextManager:
        tf.train.write_graph(session.graph.as_graph_def(), path, TF_MODEL_FILENAME, as_text=False)
        yield Blobs({
            TF_MODEL_FILENAME: LocalFileBlob(os.path.join(path, TF_MODEL_FILENAME))
        })

    def load(self, session, path):
        with session.graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(os.path.join(path, TF_MODEL_FILENAME), 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')


class TFTensorModelWrapper(ModelWrapper):
    """
    :class:`ebonite.core.objects.ModelWrapper` for tensorflow models. `.model` attribute is a list of output tensors

    :param output_tensor_names: list of output tensor names
    :param is_frozen: flag to mark frozen graphs. They will be saved with protobuf instead of saver
    """

    def __init__(self, output_tensor_names: List[str], is_frozen: bool):
        super().__init__()
        self.output_tensor_names = output_tensor_names
        self.is_frozen = is_frozen
        self._dumper = _Protobuf() if is_frozen else _Saver()
        self.__session = None

    @ModelWrapper.with_model
    @contextlib.contextmanager
    def dump(self) -> FilesContextManager:
        """
        Dumps session to temporary directory and creates :class:`~ebonite.core.objects.ArtifactCollection` from it

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        with tempfile.TemporaryDirectory(prefix='ebonite_tensor_') as tempdir:
            yield from self._dumper.dump(self._get_session(), tempdir)

    def load(self, path):
        """
        Loads graph from path

        :param path: path to load from
        """
        if self.__session is not None:
            self.__session.close()
        graph = tf.Graph()
        self.__session = tf.Session(graph=graph)

        self._dumper.load(self.__session, path)

        if isinstance(self.output_tensor_names, list):
            self.model = [graph.get_tensor_by_name(n) for n in self.output_tensor_names]
        else:
            self.model = graph.get_tensor_by_name(self.output_tensor_names)

    @ModelWrapper.with_model
    def predict(self, data):
        """
        Runs session and returns output tensor values

        :param data: data to predict
        :return: prediction
        """
        prediction = self._get_session().run(self.model, feed_dict=data)
        if isinstance(prediction, list):
            return {str(i): tensor for i, tensor in enumerate(prediction)}
        return prediction

    def _get_session(self):
        session = self.__session or tf.get_default_session()
        if session is None:
            raise ValueError('Cant work with model without session, please use inside "with session.as_default()"')
        return session


def is_graph_frozen() -> bool:
    """
    Checks if graph in current graph is frozen

    :return: `True` or `False`
    """
    return not bool(variables._all_saveable_objects())


@make_string(include_name=True)
class TFTensorHook(CanIsAMustHookMixin, ModelHook):
    """
    Hook for tensorflow models
    """

    def must_process(self, obj) -> bool:
        """
        Returns `True` if object is a tf.Tensor or list of tf.Tensors

        :param obj: obj to check
        :return: `True` or `False`
        """
        return isinstance(obj, tf.Tensor) or (isinstance(obj, list) and all(isinstance(o, tf.Tensor) for o in obj))

    def process(self, obj) -> ModelWrapper:
        """
        Creates :class:`TFTensorModelWrapper` for tensorflow model object

        :param obj: obj to process
        :return: :class:`TFTensorModelWrapper` instance
        """
        if isinstance(obj, list):
            tensor_names = [t.name for t in obj]
        else:
            tensor_names = obj.name

        return TFTensorModelWrapper(tensor_names, is_graph_frozen()).bind_model(obj)
