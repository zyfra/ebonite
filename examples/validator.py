
from threading import Lock
from typing import Optional

from pydantic import BaseModel

from ebonite.core.objects import Image
from ebonite.utils.importing import import_string
from pyjackson.utils import is_hierarchy_root, get_type_field_name, get_class_fields, is_serializable

validators_lock = Lock()
validators = {}


def create_validator(cls):
    fields = {}
    annotations = {}
    for f in get_class_fields(cls):
        if f.has_default:
            fields[f.name] = f.default
        # TODO: Check this later
        typ = f.type.__args__[0] if hasattr(f.type, '__origin__') else f.type
        if is_serializable(typ):  # проверка что поле сложный класс
            annotations[f.name] = Optional[get_validator(typ)]
        else:
            annotations[f.name] = Optional[typ]
    validator = type(f'{cls.__name__}Validator', (BaseModel,), {'__annotations__': annotations, **fields})
    return validator


def get_validator(cls_or_str):
    if not isinstance(cls_or_str, str):
        cls = cls_or_str
        classpath = f'{cls_or_str.__module__}.{cls_or_str.__name__}'
    else:
        cls = import_string(cls_or_str)
        classpath = cls_or_str

    if classpath not in validators:
        if is_hierarchy_root(cls):
            for subtype_name, subtype in cls._subtypes.items():
                validators[subtype_name] = create_validator(subtype)
        else:
            validators[classpath] = create_validator(cls)
    return validators[classpath]


def validate(payload, cls):
    if is_hierarchy_root(cls):
        classpath = payload.pop(get_type_field_name(cls))
        validator = get_validator(classpath)
        return validator.validate(payload)
    validator = get_validator(cls)
    return validator.validate(payload)


if __name__ == '__main__':
    payload = {
        'id': 1,
        'params': {'type': 'ebonite.ext.docker.DockerImage', 'name': 'aaa'}
    }

    obj = validate(payload, Image)
