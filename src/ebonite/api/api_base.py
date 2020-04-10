import json
from typing import List, Callable

import pyjackson as pj
from flask import Flask, Response, request

from ebonite.build.docker import is_docker_running
from ebonite.client.base import Ebonite
from ebonite.core.errors import ExistingProjectError, NonExistingProjectError, ExistingTaskError, NonExistingTaskError
from ebonite.core.objects.core import Project, Task
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
        self.add_endpoint(endpoint='/projects',
                          endpoint_name='projects',
                          handler=self.projects,
                          methods=['GET', 'POST'])
        self.add_endpoint(endpoint='/projects/<int:id>',
                          endpoint_name='get_update_project_by_id',
                          handler=self.get_update_delete_project_by_id,
                          methods=['GET', 'PATCH', 'DELETE'])
        self.add_endpoint(endpoint='/tasks',
                          endpoint_name='tasks',
                          handler=self.tasks,
                          methods=['GET','POST'])

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
        Checks if Docker daemon is ready to use
        :return: Response object which signifies if daemon is healthy
        """
        if is_docker_running():
            return Response(status=200, response=json.dumps({'msg':'Docker daemon is healthy'}))
        else:
            return Response(status=404, response=json.dumps(
                {'errormsg':'Failed to establish connection to docker daemon'}))

    def metadata_healthcheck(self) -> Response:
        """
        Checks if metadata repository is healthy by trying to get any project from it
        :return: Response object which signifies if metadata repository is healthy
        """
        try:
            self.ebonite.meta_repo.get_project_by_id(1)
            return Response(status=200, response=json.dumps({'msg':'Metadata repository is healthy'}))
        except Exception as e:
            return Response(status=404, response=json.dumps(
                {'errormsg':f'Error {e} while trying to establish connection to metadata repository'}))

    def artifact_healthcheck(self) -> Response:
        """
        Checks if artifact repository is healthy by trying to get any artifact from it.
        Might return NoSuchArtifactError which signifies that repository is ready to use
        :return:  Response object which signifies if artifact repository is healthy
        """
        try:
            self.ebonite.artifact_repo._get_artifact('1')
            return Response(status=200, response=json.dumps({'msg':'Artifact repository is healthy'}))
        except NoSuchArtifactError:
            return Response(status=200, response=json.dumps({'msg':'Artifact repository is healthy'}))
        except Exception as e:
            return Response(status=404, response=json.dumps(
                {'errormsg':f'Error {e} while trying to establish connection to artifact repository'}))

    def projects(self) -> Response:
        """
        Implements functionality to get all or create one project in metadata repository
        :return: Response with either all projects in json-format or deleted project
        """
        if request.method == 'GET':
            projects = self.ebonite.meta_repo.get_projects()
            return Response(status=200, response=json.dumps([pj.dumps(p) for p in projects]))
        elif request.method == 'POST':
            proj = request.get_json(force=True)
            if (proj and isinstance(proj, dict)) and proj.get('name'):
                proj = Project(name=proj['name'])
            else:
                return Response(status=404, response=json.dumps({'errormsg': 'Can not parse request body'}))
            try:
                proj = self.ebonite.meta_repo.create_project(proj)
                return Response(status=201, response=pj.dumps(proj), content_type='application/json')
            except ExistingProjectError:
                return Response(status=400, response=json.dumps({'errormsg':'Project with given name already exists'}))

    def get_update_delete_project_by_id(self, id: int) -> Response:
        """
        Implements functionality to get, update or delete project from metadata repository
        :param id: id of the project
        :return: Response object with method-specific contents
        """
        if request.method == 'GET':
            project = self.ebonite.meta_repo.get_project_by_id(id)
            if project:
                return Response(status=201, response=pj.dumps(project), content_type='application/json')
            else:
                return Response(status=404, response=json.dumps({'errormsg':f'Project with id {id} does not exist'}))
        elif request.method == 'PATCH':
            proj = request.get_json(force=True)
            if (proj and isinstance(proj, dict)) and proj.get('name'):
                proj = Project(id=id, name=proj['name'])
            else:
                return Response(status=404, response=json.dumps({'errormsg': 'Can not parse request body'}))
            try:
                self.ebonite.meta_repo.update_project(proj)
                return Response(status=204)
            except NonExistingProjectError:
                return Response(status=400, response=json.dumps({'errormsg':f'Project with id {id} does not exist'}))
        elif request.method == 'DELETE':
            # TODO: Test cascade deletion after implementing tasks api
            cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
            proj = self.ebonite.meta_repo.get_project_by_id(id)
            if not proj:
                return Response(status=404, response=json.dumps({'errormsg':f'Project with id {id} does not exist'}))
            if cascade:
                self.ebonite.delete_proj_cascade(proj)
                return Response(status=204)
            else:
                self.ebonite.meta_repo.delete_project(proj)
                return Response(status=204)

    def tasks(self):
        # TODO: Think about error handling done by app, especially cases which aren't covered by documentation
        if request.method == 'GET':
            proj_id = request.args.get('project_id')
            if proj_id and proj_id.isnumeric():
                proj = self.ebonite.meta_repo.get_project_by_id(int(proj_id))
                if proj:
                    return Response(status=200, response=json.dumps([pj.dumps(t) for t in proj.tasks]))
                else:
                    return Response(status=404, response=json.dumps(
                        {'errormsg':f'Project with id {proj_id} is not found'}))
            else:
                return Response(status=400, response=json.dumps(
                    {'errormsg':'You should provide valid project_id as URL parameter'}))
        elif request.method == 'POST':
            body = request.get_json(force=True)
            proj_id = body.get('project_id')
            task_name = body.get('name')
            if proj_id and task_name:
                task = Task(name=task_name,project_id=int(proj_id))
                try:
                    task = self.ebonite.meta_repo.create_task(task)
                    return Response(status=201, response=pj.dumps(task))
                except ExistingTaskError:
                    return Response(status=404, response=json.dumps(
                        {'errormsg': f'Task with name {task_name} already exists'}))
            else:
                return Response(status=400,
                                response={'errormsg':'Request body should contain valid task_name and project_id'})







