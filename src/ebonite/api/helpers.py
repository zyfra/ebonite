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
    obj_type: str
    obj_id: int

    @validator('obj_type')
    def obj_type_val(cls, v):
        assert v in ['pipeline', 'model'], 'obj_type should be one of pipeline/model'
        return v
