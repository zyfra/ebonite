from typing import Optional, Mapping, Union
from pydantic import BaseModel, validator
import importlib
from pyjackson.utils import get_class_fields, has_hierarchy, is_hierarchy_root
import typing


class ProjectIdValidator(BaseModel):
    project_id: int


class TaskIdValidator(BaseModel):
    task_id: int


class ModelIdValidator(BaseModel):
    model_id: int


class ImageIdValidator(BaseModel):
    image_id: int


class EnvironmentIdValidator(BaseModel):
    environment_id: int


class BuildableValidator(BaseModel):
    type: str
    server_type: str
    model_id: Optional[int] = None
    pipeline_id: Optional[int] = None

    @validator('model_id', pre=True, always=True, whole=True)
    def obj_type_val(cls, v, values):
        if not values.get('pipeline_id') and not v:
            raise ValueError('Either model_id or pipeline_id must be provided')
        return v


class RegistryValidator(BaseModel):
    type: str
    host: Optional[str]


class ImageParamsValidator(BaseModel):
    # for now it only fits DockerImage as we don't have any Params implementations besides that
    type: str
    name: str
    tag = 'latest'
    repository: Optional[str]
    registry: Optional[RegistryValidator]
    image_id: Optional[str]


class ImageUpdateValidator(BaseModel):
    id: int
    name: Optional[str]
    params: Optional[ImageParamsValidator]
    buildable: Optional[BuildableValidator]
    task_id: int
    environment_id: Optional[int]
    author: Optional[str]


class InstanceParamsValidator(BaseModel):
    type: str
    name: str
    container_id: Optional[str]
    port_mapping: Optional[Mapping[str, Union[str, int]]]
    params: Optional[Mapping[str, Union[str, int]]]


class InstanceUpdateValidator(BaseModel):
    id: int
    name: Optional[str]
    params: Optional[InstanceParamsValidator]
    image_id: int
    author: Optional[str]
    environment_id: Optional[int]


class DockerImageValidator(BaseModel):
    """"""


class DockerRegistryValidator(BaseModel):
    """"""


class RemoteRegistryValidator(BaseModel):
    """"""


validators_dict = {
    'ebonite.ext.docker.base.DockerImage': DockerImageValidator,
    'ebonite.ext.docker.base.DockerRegistry': DockerRegistryValidator,
    'ebonite.ext.docker.base.RemoteRegistry': RemoteRegistryValidator
}

# 1. Caching
# 2. Getting hierarchy root
# 3. Setting fields mechensim 50%
def generate_val_class_fields(class_str: str):
    mod_path, class_name = '.'.join(class_str.split('.')[:-1]), class_str.split('.')[-1]
    # TODO: Error handling during import
    base_module = importlib.import_module(mod_path)
    val_cls = getattr(base_module, class_name)
    cls_fields = get_class_fields(val_cls)

    for field in cls_fields:
        if hasattr(field.type, '__origin__'):
            for arg in field.type.__args__:
                for subtype in arg._subtypes:
                    arg_cls_path = '.'.join([arg.__module__, arg.__name__])
                    # TODO: check if exist
                    # TODO: Here prolly recursion goes.
                    generate_val_class_fields(validators_dict.get(arg_cls_path), arg_cls_path)


        new_type = typing.Optional[field.type]
        # TODO: Here goes field setup for validator class

from pydantic.fields import ModelField







