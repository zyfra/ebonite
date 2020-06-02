class ClassPropertyDescriptor(object):
    """
    Wrapper which provides access to methods through property syntax
    """

    def __init__(self, f_get, f_set=None):
        self.f_get = f_get
        self.f_set = f_set

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.f_get.__get__(obj, klass)()


def classproperty(func):
    """
    Decorator for properties of classes, similar to stdlib's `property` which is limited to properties of objects

    :param func: function to decorate
    :return: wrapper which provides access to methods through property syntax
    """
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)
