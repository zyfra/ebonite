from typing import List, Callable

from flask import Flask, Response

from ebonite.build.docker import is_docker_running
from ebonite.client.base import Ebonite
from ebonite.repository.artifact.base import NoSuchArtifactError


class EboniteApi:
    """
    API that provides ability to interact with Ebonite object. Based on Flask framework
    :param name: name of the flask application
    :param config_path: path to the config which will be used to initialize Ebonite object
    :param host: host on which API will be run
    :param port: port on which API will be run
    :param debug: Control of mode in which Flask application will be run

    """
    app: Flask = None

    def __init__(self, name: str, config_path: str, host: str = '127.0.0.1', port: str = '5000', debug: bool = True):
        self.app = Flask(name)
        self.host = host
        self.port = port
        self.debug = debug
        self.config_path = config_path
        self.ebonite = None

        self.app_route_conf()

    def app_route_conf(self):
        self.app.before_first_request(self.init_ebonite)
        self.add_endpoint(endpoint='/healthcheck/docker',
                          endpoint_name='docker_healthcheck',
                          handler=self.docker_healthcheck)
        self.add_endpoint(endpoint='/healthcheck/metadata',
                          endpoint_name='metadata_healthcheck',
                          handler=self.metadata_healthcheck)
        self.add_endpoint(endpoint='/healthcheck/artifact',
                          endpoint_name='artifact_healthcheck',
                          handler=self.artifact_healthcheck)

    def run(self):
        self.app.run(host=self.host, port=self.port, debug=self.debug)

    def init_ebonite(self):
        self.ebonite = Ebonite.from_config_file(self.config_path)

    def add_endpoint(self, endpoint: str = None, endpoint_name: str = None, handler: Callable = None,
                     methods: List[str] = ['GET']):
        self.app.add_url_rule(endpoint, endpoint_name, handler, methods=methods)

    @staticmethod
    def docker_healthcheck() -> Response:
        """
        Function which checks if Docker daemon is ready to use
        :return: Response object which signifies if daemon is healthy
        """
        if is_docker_running():
            return Response(status=200, response='Docker daemon is healthy')
        else:
            return Response(status=404, response='Failed to establish connection to docker daemon')

    def metadata_healthcheck(self) -> Response:
        """
        Checks if metadata repository is healthy by trying to get any project from it
        :return: Response object which signifies if metadata repository is healthy
        """
        try:
            self.ebonite.meta_repo.get_project_by_id(1)
            return Response(status=200, response='Metadata repository is healthy')
        # TODO: Надо ограничить список ошибок
        except Exception as e:
            return Response(status=404, response=f'Error {e} while trying to '
                                                 f'establish connection to metadata repository')

    def artifact_healthcheck(self) -> Response:
        """
        Checks if artifact repository is healthy by trying to get any artifact from it.
        Might return NoSuchArtifactError which signifies that repository is ready to use
        :return:  Response object which signifies if artifact repository is healthy
        """
        try:
            self.ebonite.artifact_repo._get_artifact('1')
            return Response(status=200, response='Artifact repository is healthy')
        except NoSuchArtifactError:
            return Response(status=200, response='Artifact repository is healthy')
        except Exception as e:
            return Response(status=404, response=f'Error {e} while trying to '
                                                 f'establish connection to artifact repository')
