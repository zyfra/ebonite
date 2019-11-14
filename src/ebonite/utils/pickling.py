import dill

dill._dill._reverse_typemap['ClassType'] = type


class EbonitePickler(dill.Pickler):
    """Base class for `pickle` serializers in Ebonite. Based on `dill` library."""
    pass


class EboniteUnpickler(dill.Unpickler):
    """Base class for `pickle` deserializers in Ebonite. Based on `dill` library."""
    pass
