import pytest

from ebonite.build.helpers import validate_kwargs


class A:
    @validate_kwargs
    def method1(self, a, b, **kwargs):
        return a, b

    @validate_kwargs(allowed=['c'])
    def method2(self, a, b, **kwargs):
        return a, b, kwargs.get('c')


def test_validate_kwargs():
    a = A()

    assert a.method1(1, 2) == (1, 2)

    with pytest.raises(TypeError):
        a.method1(1, 2, 3)

    with pytest.raises(TypeError):
        a.method1(1, 2, c=3)

    assert a.method2(1, 2) == (1, 2, None)
    assert a.method2(1, 2, c=3) == (1, 2, 3)

    with pytest.raises(TypeError):
        a.method2(1, 2, d=3)
