import contextlib
import json
import os
import tempfile
from abc import abstractmethod
from typing import Dict

import tensorflow as tf
from pyjackson.decorators import make_string

from ebonite.core.analyzer.base import CanIsAMustHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.artifacts import Blobs, InMemoryBlob, LocalFileBlob
from ebonite.core.objects.wrapper import FilesContextManager, LibModelWrapperMixin, ModelIO, ModelWrapper

TF_MODEL_FILENAME = 'graph'


class _TfModel:
    def __init__(self, tensors, session=None):
        self.tensors = tensors
        self.__session = session

        if isinstance(tensors, list):
            self.tensor_names = [t.name for t in tensors]
        else:
            self.tensor_names = tensors.name

        self.is_frozen = self._is_graph_frozen()

    def predict(self, input_data):
        """
        Runs session and returns output tensor values

        :param input_data: data to predict
        :return: prediction
        """
        prediction = self.get_session().run(self.tensors, feed_dict=input_data)
        if isinstance(prediction, list):
            return {str(i): tensor for i, tensor in enumerate(prediction)}
        return prediction

    def get_session(self):
        session = self.__session or tf.get_default_session()
        if session is None:
            raise ValueError('Cant work with model without session, please use inside "with session.as_default()"')
        return session

    def close_session(self):
        if self.__session is not None:
            self.__session.close()

    @staticmethod
    def _is_graph_frozen() -> bool:
        """
        Checks if graph in current graph is frozen

        :return: `True` or `False`
        """
        from tensorflow.python.ops import variables
        return not bool(variables._all_saveable_objects())


class _TFDump:
    """
    Base class for tf dumping method
    """

    @abstractmethod
    def dump(self, session, path) -> FilesContextManager:
        pass  # pragma: no cover

    @abstractmethod
    def load(self, session, path) -> tf.Graph:
        pass  # pragma: no cover


class _Saver(_TFDump):
    """
    :class:`_TFDump` implementation with tf.train.Saver
    """

    @contextlib.contextmanager
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

    @contextlib.contextmanager
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


class TFTensorModelIO(ModelIO):
    """
    :class:`ebonite.core.objects.ModelIO` for tensorflow models. Model is a `_TfModel` instance
    """
    meta_json = 'meta.json'

    @contextlib.contextmanager
    def dump(self, model: _TfModel) -> FilesContextManager:
        """
        Dumps session to temporary directory and creates :class:`~ebonite.core.objects.ArtifactCollection` from it

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        with tempfile.TemporaryDirectory(prefix='ebonite_tensor_') as tempdir:
            dumper = self._get_dumper(model.is_frozen)
            with dumper.dump(model.get_session(), tempdir) as artifact:
                meta = json.dumps([model.tensor_names, model.is_frozen]).encode('utf-8')
                yield artifact + Blobs({self.meta_json: InMemoryBlob(meta)})

    def load(self, path) -> _TfModel:
        """
        Loads graph from path

        :param path: path to load from
        """
        with open(os.path.join(path, self.meta_json)) as f:
            tensor_names, is_frozen = json.load(f)
        dumper = self._get_dumper(is_frozen)

        graph = tf.Graph()
        session = tf.Session(graph=graph)

        dumper.load(session, path)

        if isinstance(tensor_names, list):
            tensors = [graph.get_tensor_by_name(n) for n in tensor_names]
        else:
            tensors = graph.get_tensor_by_name(tensor_names)

        return _TfModel(tensors, session)

    @staticmethod
    def _get_dumper(is_frozen):
        return _Protobuf() if is_frozen else _Saver()


class TFTensorModelWrapper(LibModelWrapperMixin):
    """
    :class:`ebonite.core.objects.ModelWrapper` for tensorflow models. `.model` attribute is a list of output tensors
    """
    libraries = [tf]

    def __init__(self):
        super().__init__(TFTensorModelIO())

    def _exposed_methods_mapping(self) -> Dict[str, str]:
        return {
            'predict': 'predict'
        }

    def load(self, path):
        self._close_session_if_any()
        super().load(path)

    def bind_model(self, model, input_data=None, **kwargs):
        self._close_session_if_any()
        return super().bind_model(_TfModel(model), input_data, **kwargs)

    def _close_session_if_any(self):
        if self.model is not None:
            self.model.close_session()


@make_string(include_name=True)
class TFTensorHook(CanIsAMustHookMixin, BindingModelHook):
    """
    Hook for tensorflow models
    """
    valid_types = [tf.Tensor, list]

    # here we couldn't use `TypeHookMixin` as we expect lists of `tf.Tensor`s only
    def must_process(self, obj) -> bool:
        """
        Returns `True` if object is a tf.Tensor or list of tf.Tensors

        :param obj: obj to check
        :return: `True` or `False`
        """
        return isinstance(obj, tf.Tensor) or (isinstance(obj, list) and all(isinstance(o, tf.Tensor) for o in obj))

    def _wrapper_factory(self) -> ModelWrapper:
        """
        Creates :class:`TFTensorModelWrapper` for tensorflow model object

        :return: :class:`TFTensorModelWrapper` instance
        """
        return TFTensorModelWrapper()
