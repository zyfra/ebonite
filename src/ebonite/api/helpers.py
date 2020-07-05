from json import loads

import pyjackson as pj
from pydantic import BaseModel


def dumps_pj(pyjackson_obj):
    return loads(pj.dumps(pyjackson_obj))


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
