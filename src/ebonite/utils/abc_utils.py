IS_ABSTRACT_METHOD_FIELD = '__isabstractmethod__'


def is_abstract_method(cls_or_method, method_name=None):
    """
    Checks that given method is abstract (has no body and should be implemented by subclass)

    :param cls_or_method: either a class in which method `method_name` is found or method itself
    :param method_name: unused if `cls_or_method` is a method or name of method to look in `cls_or_method` class for
    :return: boolean flag
    """
    if isinstance(cls_or_method, type):
        method = getattr(cls_or_method, method_name)
    else:
        method = cls_or_method

    return hasattr(method, IS_ABSTRACT_METHOD_FIELD) and getattr(method, IS_ABSTRACT_METHOD_FIELD)
