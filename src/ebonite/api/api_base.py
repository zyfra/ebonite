from flasgger import Swagger
from flask import Flask

from ebonite.api.environments import environments_blueprint
from ebonite.api.errors import errors_blueprint
from ebonite.api.healthchecks import healthcheck_blueprint
from ebonite.api.images import images_blueprint
from ebonite.api.instances import instances_blueprint
from ebonite.api.models import models_blueprint
from ebonite.api.projects import project_blueprint
from ebonite.api.tasks import task_blueprint
from ebonite.client.base import Ebonite


class EboniteAPI:
    """
    API that provides ability to interact with Ebonite object. Based on Flask framework

    :param name: name of the flask application
    :param config_path: path to the config which will be used to initialize Ebonite object
    :param host: host on which API will be run
    :param port: port on which API will be run
    :param debug: Control of mode in which Flask application will be run

    """
    app: Flask = None
    blueprints = [healthcheck_blueprint, project_blueprint, task_blueprint, errors_blueprint,
                  models_blueprint, images_blueprint, environments_blueprint, instances_blueprint]

    def __init__(self, name: str, config_path: str, host: str = '127.0.0.1', port: str = '5000', debug: bool = True):
        self.app = Flask(name)
        self.host = host
        self.port = port
        self.debug = debug
        self.config_path = config_path
        self.ebonite = None

        self.init_ebonite()
        self.configure_app()
        Swagger(self.app)

    def run(self):
        self.app.run(host=self.host, port=self.port, debug=self.debug)

    def init_ebonite(self):
        self.ebonite = Ebonite.from_config_file(self.config_path)

    def configure_app(self):
        for blueprint in self.blueprints:
            self.app.register_blueprint(blueprint(self.ebonite))
