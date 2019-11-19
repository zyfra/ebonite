import pytest
from pyjackson.core import Comparable
from pyjackson.decorators import make_string

from ebonite.utils.index_dict import IndexDict, IndexDictAccessor


@make_string
class Entry(Comparable):
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


@pytest.fixture
def index_dict():
    return IndexDict[Entry]('id', 'name')


@pytest.fixture
def entry():
    return Entry('a', 'b')


@pytest.fixture
def accessor(index_dict: IndexDict):
    return IndexDictAccessor(index_dict)


def test_add(index_dict: IndexDict[Entry], entry: Entry):
    index_dict.add(entry)
    assert len(index_dict) == 1
    assert index_dict.index[entry.name] == entry.id
    assert index_dict.get(entry.id) == entry
    assert index_dict[entry.id] == entry
    assert index_dict.get_index(entry.name) == entry
    assert index_dict.get_index(entry.name, None) == entry


def test_add_no_index(index_dict: IndexDict[Entry], entry: Entry):
    with pytest.raises(KeyError):
        index_dict['c'] = entry


def test_get_default(index_dict: IndexDict[Entry]):
    assert index_dict.get_index('nonexising', None) is None


def test_reindex(index_dict: IndexDict[Entry], entry: Entry):
    index_dict.add(entry)

    old_index = index_dict.index
    index_dict.index = None

    index_dict.reindex()

    print(index_dict.__class__.__module__)
    assert index_dict.index == old_index


def test_clear(index_dict: IndexDict[Entry], entry: Entry):
    index_dict.add(entry)
    index_dict.clear()
    assert len(index_dict) == 0
    assert len(index_dict.index) == 0
    with pytest.raises(KeyError):
        _ = index_dict['a']


def test_delete(index_dict: IndexDict[Entry], entry: Entry):
    index_dict.add(entry)
    del index_dict[entry.id]

    assert len(index_dict) == 0
    assert index_dict.index.get(entry.name, None) is None
    assert index_dict.get(entry.id) is None
    with pytest.raises(KeyError):
        _ = index_dict[entry.id]

    assert index_dict.get_index(entry.name, None) is None


def test__str__(index_dict: IndexDict, entry: Entry):
    index_dict.add(entry)
    assert str(index_dict) == '<IndexDict>{b[a]=%s}' % str(entry)


def test_accessor_get(accessor: IndexDictAccessor, entry: Entry):
    accessor.data.add(entry)
    assert accessor[entry.id] == entry
    assert accessor(entry.name) == entry
    assert entry.id in accessor
    assert accessor.contains(entry.name)
    assert len(accessor) == 1
    assert next(iter(accessor)) == entry.id
    assert list(accessor.items()) == [('a', entry)]


def test_accessor_set(accessor: IndexDictAccessor, entry: Entry):
    with pytest.raises(TypeError):
        accessor[entry.id] = entry


def test_accessor_in(accessor: IndexDictAccessor, entry: Entry):
    accessor.data.add(entry)


def test_accessor__str__(accessor, entry):
    accessor.data.add(entry)
    assert str(accessor) == '<Accessor>' + str(accessor.data)
