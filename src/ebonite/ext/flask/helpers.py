import os

from ebonite.build import build_model_docker
from ebonite.core.objects import core
from ebonite.ext.flask import FlaskServer

TEMPLATES_DIR = 'build_templates'


def build_model_flask_docker(image_name: str, model: 'core.Model', image_tag='latest', force_overwrite=False, debug=False):
    """
    Builds flask docker image with nginx and uwsgi from Model instance

    :param image_name: docker image name to create
    :param model: model to create image
    :param image_tag: docker image tag
    :param force_overwrite: force overwrite image if it exists
    :param debug: run server in debug mode
    """
    kwargs = {
        'templates_dir': os.path.join(os.path.dirname(__file__), TEMPLATES_DIR),
        'run_cmd': '["/usr/bin/supervisord"]'
    }
    build_model_docker(
        image_name, model, FlaskServer(), image_tag, force_overwrite, debug, **kwargs
    )
