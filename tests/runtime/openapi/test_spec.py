from typing import Dict, List

import pytest
from pyjackson.core import ArgList, Field, Signature

from ebonite.core.objects.dataset_type import FilelikeDatasetType
from ebonite.runtime.interface.typing import TypeWithSpec
from ebonite.runtime.openapi.spec import _field_to_schema, create_spec, make_array, make_object, type_to_schema


def test_make_object__empty():
    assert make_object() == {'type': 'object'}


def test_make_object__non_empty_required():
    field = Field('field', int, False)
    obj = make_object([field])
    assert obj == {
        'type': 'object',
        'properties': {'field': _field_to_schema(field)},
        'required': ['field']
    }


def test_make_object__non_empty_not_required():
    field = Field('field', int, True, 5)
    obj = make_object([field])
    assert obj == {
        'type': 'object',
        'properties': {'field': _field_to_schema(field)}
    }


def test_make_object__additional_and_default():
    obj = make_object(None, int, True, 'DEFAULT')
    assert obj == {
        'type': 'object',
        'additionalProperties': type_to_schema(int),
        'default': 'DEFAULT'
    }


def test_make_array():
    arr = make_array(int)
    assert arr == {
        'type': 'array',
        'items': type_to_schema(int)
    }


def test_make_array__min():
    arr = make_array(int, minimum_size=10)
    assert arr == {
        'type': 'array',
        'items': type_to_schema(int),
        'minItems': 10
    }


def test_make_array__max():
    arr = make_array(int, maximum_size=10)
    assert arr == {
        'type': 'array',
        'items': type_to_schema(int),
        'maxItems': 10
    }


def test_make_array__default():
    arr = make_array(int, has_default=True, default=[1])
    assert arr == {
        'type': 'array',
        'items': type_to_schema(int),
        'default': [1]
    }


def test_type_to_schema__builtin_no_default():
    assert type_to_schema(int, False) == {'type': 'integer'}


def test_type_to_schema__builtin_default():
    assert type_to_schema(int, True, 5) == {'type': 'integer', 'default': 5}


def test_type_to_schema__generic_map():
    assert type_to_schema(Dict[str, int], False) == {
        'type': 'object',
        'additionalProperties': type_to_schema(int)
    }


def test_type_to_schema__generic_map_not_str_key():
    with pytest.raises(ValueError):
        type_to_schema(Dict[int, int], False)


def test_type_to_schema__generic_list():
    assert type_to_schema(List[int], False) == {
        'type': 'array',
        'items': type_to_schema(int)
    }


def test_type_to_schema__with_spec():
    class MyTypeWithSpec(TypeWithSpec):
        def get_spec(self) -> ArgList:
            return [Field('field', int, False)]

    assert type_to_schema(MyTypeWithSpec(), False) == {
        'type': 'object',
        'properties': {'field': type_to_schema(int)},
        'required': ['field']
    }


def test_type_to_schema__with_spec__list():
    class MyTypeWithSpec(TypeWithSpec):
        def get_spec(self) -> ArgList:
            return [Field('field', int, False)]

        def is_list(self):
            return True

        def list_size(self):
            return 1

    assert type_to_schema(MyTypeWithSpec(), False) == make_array(int, 1, 1)


def test_type_to_schema__with_spec__list_different_types():
    class MyTypeWithSpec(TypeWithSpec):
        def get_spec(self) -> ArgList:
            return [Field('field', int, False), Field('field', str, False)]

        def is_list(self):
            return True

        def list_size(self):
            return 1

    with pytest.raises(ValueError):
        type_to_schema(MyTypeWithSpec(), False)


def test_type_to_schema__class():
    class Holder:
        def __init__(self, field: int):
            self.field = field

    assert type_to_schema(Holder, False) == {
        'type': 'object',
        'properties': {'field': type_to_schema(int)},
        'required': ['field']
    }


def test_create_spec__no_file():
    field = Field('field', int, False)
    spec = create_spec('mymethod', Signature([field], field))

    assert spec == {
        'definitions': {
            'error': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'ok': {'type': 'boolean'}}
            },
            'request_mymethod': {
                'type': 'object',
                'properties': {'field': {'type': 'integer'}}
            },
            'response_mymethod': {
                'type': 'object',
                'properties': {'data': {'type': 'integer'},
                               'ok': {'type': 'boolean'}}
            }
        },
        'parameters': [{'in': 'body',
                        'name': 'body',
                        'required': True,
                        'schema': {'$ref': '#/definitions/request_mymethod'}}],
        'responses': {'200': {'description': 'resp descr',
                              'schema': {'$ref': '#/definitions/response_mymethod'}},
                      '400': {'description': 'resp descr',
                              'schema': {'$ref': '#/definitions/error'}}},
        'summary': 'mymethod'
    }


def test_create_spec__with_file():
    field = Field('field', FilelikeDatasetType(), False)
    spec = create_spec('mymethod', Signature([field], field))

    assert spec == {
        'definitions': {
            'error': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'ok': {'type': 'boolean'}}
            }
        },
        'parameters': [{'description': 'field',
                        'in': 'formData',
                        'name': 'field',
                        'required': True,
                        'type': 'file'}],
        'responses': {'200': {"description": "resp descr",
                              'content': {'*/*': {
                                  'type': 'string',
                                  'format': 'binary'
                              }}},
                      '400': {'description': 'resp descr',
                              'schema': {'$ref': '#/definitions/error'}}},
        'summary': 'mymethod'
    }
