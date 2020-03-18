from typing import Dict, List, Type

from pyjackson.utils import (Field, Signature, get_class_fields, get_collection_internal_type, get_mapping_types,
                             is_collection, is_generic, is_mapping)

from ebonite.core.objects.dataset_type import FilelikeDatasetType, PrimitiveDatasetType
from ebonite.core.objects.typing import TypeWithSpec

BUILTIN_TYPES: Dict[Type, str] = {
    int: 'integer', float: 'number', str: 'string', None: 'null', bool: 'boolean',  # list:'array', dict:'object'
}


def make_object(properties: List[Field] = None,
                arbitrary_properties_type: Type = None,
                has_default=False, default=None):  # TODO nullable
    """
    Converts object type described as list of fields to OpenAPI schema definition

    :param properties: fields of object
    :param arbitrary_properties_type: (optional) required type for properties which are not specified in `properties`
    :param has_default: specifies whether given type has default value
    :param default: specifies default value for given type
    :return: dict with OpenAPI schema definition
    """

    result = {
        'type': 'object',
    }
    if properties is not None:
        result['properties'] = {a.name: _field_to_schema(a) for a in properties}
        required = [a.name for a in properties if not a.has_default]
        if required:
            result['required'] = required
    if arbitrary_properties_type is not None:
        result['additionalProperties'] = type_to_schema(arbitrary_properties_type)
    if has_default:
        result['default'] = default

    return result


def make_array(item_type: Type, minimum_size=None, maximum_size=None, has_default=False, default=None):
    """
    Converts array type described as type of its items and range of possible sizes to OpenAPI schema definition

    :param item_type: type of items in array
    :param minimum_size: minimal possible size of array
    :param maximum_size: maximal possible size of array
    :param has_default: specifies whether given type has default value
    :param default: specifies default value for given type
    :return: dict with OpenAPI schema definition
    """

    result = {
        'type': 'array',
        'items': type_to_schema(item_type)
    }
    if minimum_size is not None:
        result['minItems'] = minimum_size
    if maximum_size is not None:
        result['maxItems'] = maximum_size
    if has_default:
        result['default'] = default
    return result


def _field_to_schema(field: Field):
    return type_to_schema(field.type, field.has_default, field.default)


def type_to_schema(field_type, has_default=False, default=None):
    """
    Facade method converting arbitrary type to OpenAPI schema definitions.
    Has special support for builtins, collections and instances of :class:`.TypeWithSpec` subclasses.

    :param field_type: type to generate schema for
    :param has_default: specifies whether given type has default value
    :param default: specifies default value for given type
    :return: dict with OpenAPI schema definition
    """
    if field_type in BUILTIN_TYPES:
        result = {'type': BUILTIN_TYPES[field_type]}
        if has_default:
            result['default'] = default
        return result

    elif is_generic(field_type):
        if is_collection(field_type):
            return make_array(get_collection_internal_type(field_type), has_default=has_default, default=default)
        elif is_mapping(field_type):
            kt, vt = get_mapping_types(field_type)
            if kt != str:
                raise ValueError('Only string keys supported')
            return make_object(arbitrary_properties_type=vt, has_default=has_default, default=default)

    elif issubclass(field_type, TypeWithSpec):
        if issubclass(field_type, PrimitiveDatasetType):
            return type_to_schema(field_type.to_type, has_default, default)

        # noinspection PyArgumentList
        spec = field_type.get_spec()
        # noinspection PyArgumentList
        is_list = field_type.is_list()
        # noinspection PyArgumentList
        list_size = field_type.list_size()
        if is_list:
            item_types = set(a.type for a in spec)
            if len(item_types) > 1:
                raise ValueError('All items must be of same type for {}'.format(field_type))
            item_type = next(iter(item_types))
            return make_array(item_type, list_size, list_size)
        else:
            return make_object(spec)
        # return schema_from_typespec(field)
    else:
        return make_object(get_class_fields(field_type))


def create_spec(method_name: str, signature: Signature):
    """
    Generates OpenAPI schema definition for given method

    :param method_name: name of method
    :param signature: types of arguments and type of return value
    :return: dict with OpenAPi schema definition
    """

    error_def = {
        'type': 'object',
        'properties': {
            'ok': {'type': 'boolean'},
            'error': {'type': 'string'}
        }
    }
    value_args = [a for a in signature.args if not issubclass(a.type, FilelikeDatasetType)]
    file_args = [a for a in signature.args if issubclass(a.type, FilelikeDatasetType)]

    if issubclass(signature.output.type, FilelikeDatasetType):
        good_response = {"description": "successful response",
                         'content': {"multipart/form-data": {
                             'type': 'string',
                             'format': 'binary'
                         }}}
    else:
        response_def = {
            'type': 'object',
            'properties': {
                'ok': {'type': 'boolean'},
                'data': type_to_schema(signature.output.type, False, None)
            }
        }
        good_response = {"description": "successful response",
                         "content": {"application/json": {"schema": response_def}}}

    if value_args and file_args:
        raise ValueError('Both JSON and file data at the same time is not supported')

    if value_args:
        json_body_def = {
            'type': 'object',
            'properties': {
                a.name: _field_to_schema(a) for a in value_args
            }
        }
        request_body = {'required': True,
                        "content": {"application/json": {'schema': json_body_def}}}
    elif file_args:
        files_body_def = {
            'type': 'object',
            'properties': {
                a.name: {'type': 'string', 'format': 'binary'} for a in file_args
            }
        }
        request_body = {'required': True,
                        "content": {"multipart/form-data": {'schema': files_body_def}}}
    else:
        request_body = {'required': False}

    bad_response = {"description": "incorrect request",
                    "content": {"application/json": {"schema": error_def}}}

    return {
        "summary": f"Calls '{method_name}' method on model",
        "requestBody": request_body,
        "responses": {
            "200": good_response,
            "400": bad_response
        }
    }
