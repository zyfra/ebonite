from pydantic import BaseModel


class IdValidator(BaseModel):
    #TODO: make a lot of optional fields? won't work with None - think about it
    id: int
