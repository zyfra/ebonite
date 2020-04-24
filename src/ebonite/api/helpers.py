from pydantic import BaseModel


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
