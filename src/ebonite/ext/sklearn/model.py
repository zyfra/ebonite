from typing import Dict

from pyjackson.decorators import make_string
from sklearn.base import ClassifierMixin

from ebonite.core.analyzer.base import LibHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.wrapper import ModelWrapper, PickleModelWrapper


class SklearnModelWrapper(PickleModelWrapper):
    """
    `pickle`-based :class:`.ModelWrapper` implementation for `scikit-learn` models
    """

    def _exposed_methods_mapping(self) -> Dict[str, str]:
        ret = {
            'predict': 'predict'
        }
        if isinstance(self.model, ClassifierMixin):
            ret['predict_proba'] = 'predict_proba'
        return ret


@make_string(include_name=True)
class SklearnHook(ModelHook, LibHookMixin):
    """
    :class:`ebonite.core.analyzer.model.ModelHook` implementation for `scikit-learn` models
    which uses :class:`SklearnModelWrapper`
    """

    base_module_name = 'sklearn'

    def process(self, obj, **kwargs) -> ModelWrapper:
        return SklearnModelWrapper().bind_model(obj, **kwargs)
