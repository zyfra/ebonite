from functools import wraps
from typing import List, Callable
from pyjackson.utils import get_function_fields, turn_args_to_kwargs


def validate_kwargs(f=None, *, allowed: List[str] = None, allowed_funcs: List[Callable] = None):

    def inner(func):
        all_fields = allowed or []
        if allowed_funcs is not None:
            all_fields += [field.name for func in allowed_funcs for field in get_function_fields(func, False)]
        all_fields = set(all_fields)
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
