from ebonite.runtime.interface.base import Interface
from ebonite.runtime.server.base import Server
from ebonite.utils.fs import current_module_path


class CvStreamingServer(Server):

    additional_sources = [
        current_module_path('build', 'app.py')  # replace stub in base image
    ]

    additional_options = {'docker': {
        'templates_dir': current_module_path('build'),
        'run_cmd': False,  # base image has already specified command
        'base_image': 'nvcr.io/nvidia/tensorrt:20.07.1-py3'
    }}

    def run(self, executor: Interface):
        pass
