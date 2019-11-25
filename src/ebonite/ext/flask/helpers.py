import os

from ebonite.build import build_model_docker
from ebonite.core.objects import core
from ebonite.ext.flask import FlaskServer

TEMPLATES_DIR = 'build_templates'


def build_model_flask_docker(image_name: str, model: 'core.Model', image_tag='latest', force_overwrite=False):
    kwargs = {
        'templates_dir': os.path.join(os.path.dirname(__file__), TEMPLATES_DIR),
        'run_cmd': '["/usr/bin/supervisord"]'
    }
    build_model_docker(
        image_name, model, FlaskServer(), image_tag, force_overwrite, **kwargs
    )
