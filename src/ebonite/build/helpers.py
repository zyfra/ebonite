from functools import wraps
from typing import List
from pyjackson.utils import get_function_fields, turn_args_to_kwargs


def validate_kwargs(f=None, *, allowed: List[str] = None):

    def inner(func):
        all_fields = set(allowed or [])
        fields = get_function_fields(func, False)
        all_fields.update(field.name for field in fields)

        @wraps(func)
        def inner_inner(self, *args, **kwargs):
            if len(args) > len(fields):
                raise TypeError(
                    f'{func.__name__}() takes {len(fields)} positional arguments but {len(args)} were given')
            kwargs = turn_args_to_kwargs(func, args, kwargs, False)
            extra_kwargs = set(kwargs.keys()).difference(all_fields)
            if len(extra_kwargs) > 0:
                raise TypeError(f'{extra_kwargs} are an invalid keyword arguments for this function')
            return func(self, **kwargs)

        return inner_inner

    if f is None:
        return inner
    return inner(f)
