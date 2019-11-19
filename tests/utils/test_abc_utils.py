from abc import abstractmethod

from ebonite.utils.abc_utils import is_abstract_method


class MyClass:
    def not_abstract(self):
        pass

    @abstractmethod
    def abstract(self):
        pass


def test_is_abstract_method():
    assert is_abstract_method(MyClass.abstract)
    assert is_abstract_method(MyClass, 'abstract')

    assert not is_abstract_method(MyClass.not_abstract)
    assert not is_abstract_method(MyClass, 'not_abstract')
