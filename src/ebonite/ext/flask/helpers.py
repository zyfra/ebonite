import os
from typing import Union

from ebonite.build.docker import DockerImage
from ebonite.build.helpers import build_model_docker
from ebonite.core.objects import core
from ebonite.ext.flask.server import FlaskServer

TEMPLATES_DIR = 'build_templates'


def build_model_flask_docker(image_params: Union[str, DockerImage], model: 'core.Model',
                             force_overwrite=False, debug=False) -> 'core.Image':
    """
    Builds flask docker image with nginx and uwsgi from Model instance

    :param image_params: params (or simply name) for docker image to be built
    :param model: model to create image
    :param force_overwrite: force overwrite image if it exists
    :param debug: run server in debug mode
    """
    kwargs = {
        'templates_dir': os.path.join(os.path.dirname(__file__), TEMPLATES_DIR),
        'run_cmd': '["/usr/bin/supervisord"]'
    }
    return build_model_docker(
        image_params, model, FlaskServer(), force_overwrite, debug, **kwargs
    )
