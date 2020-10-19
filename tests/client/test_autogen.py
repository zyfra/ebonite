import inspect
from unittest.mock import MagicMock

import pytest

from ebonite import Ebonite
from ebonite.client.autogen import AUTOGEN_CLASSES, clear, find_exposed_methods
from ebonite.client.expose import ExposedMethod, get_exposed_method
from ebonite.core.objects.core import EboniteObject
from ebonite.repository import ArtifactRepository, MetadataRepository
from tests.conftest import MockMixin


def test_get_declaration():
    def decorator(*args, **kwargs):
        return lambda x: x

    class A:
        @ExposedMethod('new_name')
        @decorator()
        @decorator(1,
                   2,

                   3)
        def method(self, a: int = 0,
                   kek: str = None,

                   lol=None):  # comment

            """docs"""

            return 'body'

    expected = """
    def new_name(self, a: int = 0,
                   kek: str = None,
                   lol=None):  # comment
""".strip()
    assert get_exposed_method(A.method).get_declaration() == expected


@pytest.mark.parametrize('base', AUTOGEN_CLASSES)
def test_all_exposed(base):
    assert find_exposed_methods(base) == []


object_exposed = [e for base in AUTOGEN_CLASSES
                  for e in find_exposed_methods(base, False) if issubclass(base, EboniteObject)]


@pytest.mark.parametrize('exposed', object_exposed, ids=[e.name for e in object_exposed])
def test_objects(exposed: ExposedMethod, mock_ebnt):
    method = getattr(mock_ebnt, exposed.name, None)
    args = [i for i, _ in enumerate(exposed.get_signature().args)]
    obj = type('obj', (), {exposed.original_name: MagicMock(name=exposed.original_name)})()
    method(obj, *args)
    getattr(obj, exposed.original_name).assert_called_with(*args)


meta_exposed = [e for e in find_exposed_methods(MetadataRepository, False)]


class MockMeta(MetadataRepository, MockMixin, proxy_mode=False):
    pass


class MockArt(ArtifactRepository, MockMixin, proxy_mode=False):
    pass


@pytest.fixture
def mock_ebnt():
    class MockEbonite(Ebonite):
        _bind = MagicMock(name='_bind')

        def __init__(self):
            super().__init__(MockMeta(), MockArt())

    return MockEbonite()


@pytest.mark.parametrize('exposed', meta_exposed, ids=[e.name for e in meta_exposed])
def test_metadata(exposed: ExposedMethod, mock_ebnt):
    method = getattr(mock_ebnt, exposed.name, None)
    args = [i for i, _ in enumerate(exposed.get_signature().args)]
    method(*args)
    mock_ebnt._bind.assert_called()
    getattr(mock_ebnt.meta_repo, exposed.original_name).assert_called_with(*args)


all_exposed = [e for base in AUTOGEN_CLASSES for e in find_exposed_methods(base, False)]


@pytest.mark.parametrize('exposed', all_exposed, ids=[e.name for e in all_exposed])
def test_exposed_code_equals(exposed: ExposedMethod):
    method = getattr(Ebonite, exposed.name, None)
    generated = exposed.generate_code()
    if method is None:
        return  # separate test for this
    actual = inspect.getsource(method)

    def striplines(s):
        return '\n'.join(line.strip() for line in s.split('\n'))

    assert striplines(generated.strip()) == striplines(actual.strip())


def test_autogen__clear(tmpdir):
    source = """
    # AUTOGEN
    def method_to_remove(x):
       return x
    # AUTOGEN END
    def method_to_remain(x):
       return x"""
    expected = """
    # AUTOGEN

    # AUTOGEN END
    def method_to_remain(x):
       return x"""
    p = tmpdir.mkdir('temp').join('temp.py')
    p.write(source)
    clear(p, dry_run=False)
    assert len(p.read()) == len(expected)
    assert p.read() == expected
