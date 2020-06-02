from ebonite.core.objects.core import Buildable
from ebonite.utils.importing import import_string


class BuildableWithServer(Buildable):
    def __init__(self, server_type: str):
        self.server_type = server_type

    @property
    def server(self):
        return import_string(self.server_type)()
