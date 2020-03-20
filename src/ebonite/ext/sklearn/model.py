from typing import Dict

from pyjackson.decorators import make_string
from sklearn.base import ClassifierMixin

from ebonite.core.analyzer.base import LibHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.wrapper import ModelWrapper, PickleModelIO


class SklearnModelWrapper(ModelWrapper):
    """
    `pickle`-based :class:`.ModelWrapper` implementation for `scikit-learn` models
    """
    def __init__(self):
        super().__init__(PickleModelIO())

    def _exposed_methods_mapping(self) -> Dict[str, str]:
        ret = {
            'predict': 'predict'
        }
        if isinstance(self.model, ClassifierMixin):
            ret['predict_proba'] = 'predict_proba'
        return ret


@make_string(include_name=True)
class SklearnHook(BindingModelHook, LibHookMixin):
    """
    :class:`ebonite.core.analyzer.model.ModelHook` implementation for `scikit-learn` models
    which uses :class:`SklearnModelWrapper`
    """

    base_module_name = 'sklearn'

    def _wrapper_factory(self) -> ModelWrapper:
        return SklearnModelWrapper()
