import json
from typing import List, Callable

import pyjackson as pj
from flask import Flask, Response, request

from ebonite.build.docker import is_docker_running
from ebonite.client.base import Ebonite
from ebonite.core.errors import ExistingProjectError, NonExistingProjectError, ExistingTaskError, NonExistingTaskError
from ebonite.core.objects.core import Project, Task
from ebonite.repository.artifact.base import NoSuchArtifactError


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
        self.add_endpoint(endpoint='/healthcheck/docker', endpoint_name='docker_healthcheck',
                          handler=self.docker_healthcheck)
        self.add_endpoint(endpoint='/healthcheck/metadata', endpoint_name='metadata_healthcheck',
                          handler=self.metadata_healthcheck)
        self.add_endpoint(endpoint='/healthcheck/artifact', endpoint_name='artifact_healthcheck',
                          handler=self.artifact_healthcheck)
        self.add_endpoint(endpoint='/projects', endpoint_name='get_projects', handler=self.get_projects)
        self.add_endpoint(endpoint='/projects', endpoint_name='create_project', handler=self.create_project,
                          methods=['POST'])
        self.add_endpoint(endpoint='/projects/<int:id>', endpoint_name='get_project', handler=self.get_project)
        self.add_endpoint(endpoint='/projects/<int:id>', endpoint_name='update_project', handler=self.update_project,
                          methods=['PATCH'])
        self.add_endpoint(endpoint='/projects/<int:id>', endpoint_name='delete_project', handler=self.delete_project,
                          methods=['DELETE'])
        self.add_endpoint(endpoint='/tasks', endpoint_name='get_tasks', handler=self.get_tasks)
        self.add_endpoint(endpoint='/tasks', endpoint_name='create_task', handler=self.create_task, methods=['POST'])
        self.add_endpoint(endpoint='/tasks/<int:id>', endpoint_name='get_task', handler=self.get_task)
        self.add_endpoint(endpoint='/tasks/<int:id>', endpoint_name='update_task', handler=self.update_task,
                          methods=['PATCH'])
        self.add_endpoint(endpoint='/tasks/<int:id>', endpoint_name='delete_task', handler=self.delete_task,
                          methods=['DELETE'])

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
            return Response(status=200, response=json.dumps({'msg': 'Docker daemon is healthy'}))
        else:
            return Response(status=404, response=json.dumps(
                {'errormsg': 'Failed to establish connection to docker daemon'}))

    def metadata_healthcheck(self) -> Response:
        """
        Checks if metadata repository is healthy by trying to get any project from it
        :return: Response object which signifies if metadata repository is healthy
        """
        try:
            self.ebonite.meta_repo.get_project_by_id(1)
            return Response(status=200, response=json.dumps({'msg': 'Metadata repository is healthy'}))
        except Exception as e:
            return Response(status=404, response=json.dumps(
                {'errormsg': f'Error {e} while trying to establish connection to metadata repository'}))

    def artifact_healthcheck(self) -> Response:
        """
        Checks if artifact repository is healthy by trying to get any artifact from it.
        Might return NoSuchArtifactError which signifies that repository is ready to use
        :return:  Response object which signifies if artifact repository is healthy
        """
        try:
            self.ebonite.artifact_repo._get_artifact('1')
            return Response(status=200, response=json.dumps({'msg': 'Artifact repository is healthy'}))
        except NoSuchArtifactError:
            return Response(status=200, response=json.dumps({'msg': 'Artifact repository is healthy'}))
        except Exception as e:
            return Response(status=404, response=json.dumps(
                {'errormsg': f'Error {e} while trying to establish connection to artifact repository'}))

    def get_projects(self) -> Response:
        """
        Gets all projects from metadata repository
        :return: All projects in database
        """
        projects = self.ebonite.meta_repo.get_projects()
        return Response(status=200, response=json.dumps([pj.dumps(p) for p in projects]))

    def create_project(self) -> Response:
        """
        Creates project in metadata repository
        :return: Response with created object or error
        """
        proj = request.get_json(force=True)
        if (proj and isinstance(proj, dict)) and proj.get('name'):
            proj = Project(name=proj['name'])
        else:
            return Response(status=404, response=json.dumps({'errormsg': 'Can not parse request body'}))
        try:
            proj = self.ebonite.meta_repo.create_project(proj)
            return Response(status=201, response=pj.dumps(proj), content_type='application/json')
        except ExistingProjectError:
            return Response(status=400, response=json.dumps({'errormsg': 'Project with given name already exists'}))

    def get_project(self, id: int) -> Response:
        """
        Gets single project from metadata repository
        :param id: id of project
        :return: Response with requested project or error
        """
        project = self.ebonite.meta_repo.get_project_by_id(id)
        if project:
            return Response(status=201, response=pj.dumps(project), content_type='application/json')
        else:
            return Response(status=404, response=json.dumps({'errormsg': f'Project with id {id} does not exist'}))

    def update_project(self, id: int) -> Response:
        """
        Changes name of project in metadata repository
        :param id: id of project
        :return: Response with code 204 or error
        """
        proj = request.get_json(force=True)
        if (proj and isinstance(proj, dict)) and proj.get('name'):
            proj = Project(id=id, name=proj['name'])
        else:
            return Response(status=404, response=json.dumps({'errormsg': 'Can not parse request body'}))
        try:
            self.ebonite.meta_repo.update_project(proj)
            return Response(status=204)
        except NonExistingProjectError:
            return Response(status=400, response=json.dumps({'errormsg': f'Project with id {id} does not exist'}))

    def delete_project(self, id: int) -> Response:
        """
        Deletes either only project or cascadely deletes everything linked to it from metadata repository
        :param id: id of project
        :return: Response with code 204 or error
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        proj = self.ebonite.meta_repo.get_project_by_id(id)
        if not proj:
            return Response(status=404, response=json.dumps({'errormsg': f'Project with id {id} does not exist'}))
        if cascade:
            self.ebonite.delete_proj_cascade(proj)
            return Response(status=204)
        else:
            self.ebonite.meta_repo.delete_project(proj)
            return Response(status=204)

    def get_tasks(self) -> Response:
        """
        Get all tasks from metadata repository for given project
        :return: Response with all project for given project or error
        """
        proj_id = request.args.get('project_id')
        if proj_id and proj_id.isnumeric():
            proj = self.ebonite.meta_repo.get_project_by_id(int(proj_id))
            if proj:
                return Response(status=200, response=json.dumps(
                    [pj.dumps(self.ebonite.meta_repo.get_task_by_id(t)) for t in proj.tasks]))
            else:
                return Response(status=404, response=json.dumps(
                    {'errormsg': f'Project with id {proj_id} is not found'}))
        else:
            # TODO: Make adequate validation method and error for it
            return Response(status=400, response=json.dumps(
                {'errormsg': 'You should provide valid project_id as URL parameter'}))

    def create_task(self) -> Response:
        """
        Creates task in metadata repository
        :return: Response with created task or error
        """
        body = request.get_json(force=True)
        proj_id = body.get('project_id')
        task_name = body.get('name')
        if proj_id and task_name:
            task = Task(name=task_name, project_id=int(proj_id))
            try:
                task = self.ebonite.meta_repo.create_task(task)
                return Response(status=201, response=pj.dumps(task))
            except ExistingTaskError:
                return Response(status=404, response=json.dumps(
                    {'errormsg': f'Task with name {task_name} already exists'}))
        else:
            return Response(status=400,
                            response={'errormsg': 'Request body should contain valid task_name and project_id'})

    def get_task(self, id: int) -> Response:
        """
        Gets task from metadata repository
        :param id: id of the task
        :return: Response with task or error
        """
        try:
            task = self.ebonite.meta_repo.get_task_by_id(id)
            return Response(status=200, response=pj.dumps(task))
        except NonExistingTaskError:
            return Response(status=404, response=json.dumps({'errormsg': f'Task with id {id} does not exist'}))

    def update_task(self, id: int) -> Response:
        """
        Changes name of task in metadata repository
        :param id: id of task
        :return: Response with 204 code or error
        """
        body = request.get_json(force=True)
        task_name = body.get('name')
        proj_id = body.get('project_id')
        if task_name and proj_id:
            task = Task(id=id, project_id=int(proj_id), name=task_name)
            try:
                self.ebonite.meta_repo.update_task(task)
                return Response(status=204)
            except NonExistingTaskError:
                return Response(status=404, response=json.dumps(
                    {'errormsg': f'Task with id {id} in project {proj_id} does not exist'}))
        else:
            return Response(status=400, response=json.dumps(
                {'errormsg': 'Request body should contain valid task_name and project id'}))

    def delete_task(self, id: int) -> Response:
        """
        Deletes either only task or cascadely deletes everything linked to it from metadata repository
        :param id: id of task
        :return: Response with 204 code or error
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        task = self.ebonite.meta_repo.get_task_by_id(id)
        if not task:
            return Response(status=404, response=json.dumps({'erromsg': f'Task with id {id} does not exist'}))
        else:
            if cascade:
                self.ebonite.delete_task_cascade(task)
                return Response(status=204)
            else:
                self.ebonite.meta_repo.delete_task(task)
                return Response(status=204)
