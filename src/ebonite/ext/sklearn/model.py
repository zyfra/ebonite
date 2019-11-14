from pyjackson.decorators import make_string

from ebonite.core.analyzer.base import LibHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.wrapper import ModelWrapper, PickleModelWrapper


class SklearnModelWrapper(PickleModelWrapper):
    """
    `pickle`-based :class:`.ModelWrapper` implementation for `scikit-learn` models
    """
    type = 'sklearn'

    def predict(self, data):
        return self.model.predict(data)


@make_string(include_name=True)
class SklearnHook(ModelHook, LibHookMixin):
    """
    :class:`ebonite.core.analyzer.model.ModelHook` implementation for `scikit-learn` models
    which uses :class:`SklearnModelWrapper`
    """

    base_module_name = 'sklearn'

    def process(self, obj) -> ModelWrapper:
        return SklearnModelWrapper().bind_model(obj)
