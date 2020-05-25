import pytest

from tests.conftest import MockMixin


class A:
    def method(self):
        """aaaa"""

    def method2(self):
        return 2


class B(A, MockMixin):
    def method(self):
        return 1


def test_mock_mixin():
    b = B()
    assert b.method() == 1
    b.method.assert_called()
    assert b.method2() == 2
    b.method2.assert_called()


def test_mock_mixin__2_instances():
    b1 = B()
    b2 = B()

    assert b1.method() == 1
    b1.method.assert_called()
    b2.method.assert_not_called()


def test_mock_call_context():
    b1 = B()
    with pytest.raises(AssertionError):
        with b1.method.called_within_context():
            pass

    with b1.method.called_within_context():
        b1.method()

    with pytest.raises(AssertionError):
        with b1.method.called_within_context():
            b1.method()

    with b1.method.called_within_context(first=False):
        b1.method()

    with pytest.raises(AssertionError):
        with b1.method.called_within_context(first=False, times=2):
            b1.method()

    with b1.method.called_within_context(first=False, times=2):
        b1.method()
        b1.method()
