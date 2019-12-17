from pyjackson.decorators import make_string
from sklearn.base import ClassifierMixin

from ebonite.core.analyzer.base import LibHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.wrapper import ModelWrapper, PickleModelWrapper


class SklearnModelWrapper(PickleModelWrapper):
    """
    `pickle`-based :class:`.ModelWrapper` implementation for `scikit-learn` models
    """

    @ModelWrapper.with_model
    def predict(self, data):
        return self.model.predict(data)

    def __getattr__(self, item):
        if item == 'predict_proba' and isinstance(self.model, ClassifierMixin):
            return self._predict_proba
        raise AttributeError(f"'{type(self)}' object has not attribute '{item}'")

    @ModelWrapper.with_model
    def _predict_proba(self, data):
        return self.model.predict_proba(data)


@make_string(include_name=True)
class SklearnHook(ModelHook, LibHookMixin):
    """
    :class:`ebonite.core.analyzer.model.ModelHook` implementation for `scikit-learn` models
    which uses :class:`SklearnModelWrapper`
    """

    base_module_name = 'sklearn'

    def process(self, obj) -> ModelWrapper:
        return SklearnModelWrapper().bind_model(obj)
