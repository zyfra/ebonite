from flask import Flask, Response

from ebonite.build.docker import is_docker_running
from ebonite.client.base import Ebonite
from ebonite.repository.artifact.base import NoSuchArtifactError


class EboniteApi:
    app = None

    def __init__(self, name, config_path, host='127.0.0.1', port='5000', debug=True):
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

    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, methods=['GET']):
        self.app.add_url_rule(endpoint, endpoint_name, handler, methods=methods)

    @staticmethod
    def docker_healthcheck():
        if is_docker_running():
            return Response(status=200, response='Docker daemon is healthy')
        else:
            return Response(status=404, response='Failed to establish connection to docker daemon')

    def metadata_healthcheck(self):
        try:
            self.ebonite.meta_repo.get_project_by_id(1)
            return Response(status=200, response='Metadata repository is healthy')
        # TODO: Надо ограничить список ошибок
        except Exception as e:
            return Response(status=404, response=f'Error {e} while trying to '
                                                 f'establish connection to metadata repository')

    def artifact_healthcheck(self):
        try:
            self.ebonite.artifact_repo._get_artifact('1')
            return Response(status=200, response='Artifact repository is healthy')
        except NoSuchArtifactError:
            return Response(status=200, response='Artifact repository is healthy')
        except Exception as e:
            return Response(status=404, response=f'Error {e} while trying to '
                                                 f'establish connection to artifact repository')
