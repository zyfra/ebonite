from typing import Optional

from pydantic import BaseModel, validator


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
