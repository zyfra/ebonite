from typing import Generic, TypeVar

T = TypeVar('T')


class IndexDict(dict, Generic[T]):
    def __init__(self, key_field, index_field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_field = key_field
        self.index_field = index_field
        self.index = {}

    def __setitem__(self, key, value):
        if key != getattr(value, self.key_field):
            raise KeyError(f'Key {key} is not equal to {self.key_field} field of {value}')
        old_value = self.get(key, None)
        if old_value is not None:
            del self.index[getattr(old_value, self.index_field)]
        super(IndexDict, self).__setitem__(key, value)
        self.index[getattr(value, self.index_field)] = key

    def add(self, value: T):
        self[getattr(value, self.key_field)] = value

    def get_index(self, key, default=...) -> T:
        if default is ...:
            return self[self.index[key]]
        else:
            key = self.index.get(key, None)
            if key is None:
                return default
            return self[key]

    def reindex(self):
        self.index = {getattr(v, self.index_field): k for k, v in self.items()}

    def clear(self) -> None:
        super(IndexDict, self).clear()
        self.index.clear()

    def __delitem__(self, key):
        value = self[key]
        del self.index[getattr(value, self.index_field)]
        super(IndexDict, self).__delitem__(key)

    def __repr__(self):
        return f'<IndexDict>{{{", ".join(f"{getattr(v, self.index_field)}[{k}]={v}" for k, v in self.items())}}}'

    def __str__(self):
        return self.__repr__()


class IndexDictAccessor(Generic[T]):
    def __init__(self, data: IndexDict[T]):
        self.data = data

    def __getitem__(self, item) -> T:
        return self.data[item]

    def __call__(self, key, default=...) -> T:
        return self.data.get_index(key, default)

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __contains__(self, item):
        return item in self.data

    def contains(self, item):
        return item in self.data.index

    def values(self):
        return self.data.values()

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def get(self, key, default=...) -> T:
        return self.data.get(key, default)

    def __repr__(self):
        return f'<Accessor>{self.data}'

    def __str__(self):
        return self.__repr__()
