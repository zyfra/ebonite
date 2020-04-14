from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pydantic import ValidationError
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.build.docker import is_docker_running
from ebonite.core.errors import (ExistingProjectError, ExistingTaskError, NonExistingProjectError, NonExistingTaskError,
                                 ProjectWithRelationshipError, TaskWithRelationshipError)
from ebonite.core.objects.core import Project, Task
from ebonite.repository.artifact.base import NoSuchArtifactError


class ProjectBody(PyjacksonModel):
    __type__ = Project


class TaskBody(PyjacksonModel):
    __type__ = Task


def healthcheck_blueprint(ebonite):
    blueprint = Blueprint('healthcheks', __name__, url_prefix='/healthchecks')

    @blueprint.route('/docker', methods=['GET'])
    def docker_healthcheck() -> Tuple[Response, int]:
        """
        Checks if Docker daemon is ready to use
        :return: Response object which signifies if daemon is healthy
        """
        if is_docker_running():
            return jsonify({'msg': 'Docker daemon is healthy'}), 200
        else:
            return jsonify({'errormsg': 'Failed to establish connection to docker daemon'}), 404

    @blueprint.route('/metadata', methods=['GET'])
    def metadata_healthcheck() -> Tuple[Response, int]:
        """
        Checks if metadata repository is healthy by trying to get any project from it
        :return: Response object which signifies if metadata repository is healthy
        """
        try:
            ebonite.meta_repo.get_project_by_id(1)
            return jsonify({'msg': 'Metadata repository is healthy'}), 200
        except Exception as e:
            return jsonify({'errormsg': f'Error {e} while trying to establish connection to metadata repository'}), 404

    @blueprint.route('/artifact', methods=['GET'])
    def artifact_healthcheck() -> Tuple[Response, int]:
        """
        Checks if artifact repository is healthy by trying to get any artifact from it.
        Might return NoSuchArtifactError which signifies that repository is ready to use
        :return:  Response object which signifies if artifact repository is healthy
        """
        try:
            ebonite.artifact_repo._get_artifact('1')
            return jsonify({'msg': 'Artifact repository is healthy'}), 200
        except NoSuchArtifactError:
            return jsonify({'msg': 'Artifact repository is healthy'}), 200
        except Exception as e:
            return jsonify({'errormsg': f'Error {e} while trying to establish connection to artifact repository'}), 404

    return blueprint


def project_blueprint(ebonite):
    blueprint = Blueprint('projects', __name__, url_prefix='/projects')

    @blueprint.route('', methods=['GET'])
    def get_projects() -> Tuple[Response, int]:
        """
        Gets all projects from metadata repository
        :return: All projects in database
        """
        projects = ebonite.meta_repo.get_projects()
        return jsonify({'projects': [pj.dumps(p) for p in projects]}), 200

    @blueprint.route('', methods=['POST'])
    def create_project() -> Tuple[Response, int]:
        """
        Creates project in metadata repository
        :return: Response with created object or error
        """
        proj = ProjectBody.from_data(request.get_json(force=True))
        try:
            proj = ebonite.meta_repo.create_project(proj)
            return jsonify({'project': pj.dumps(proj)}), 201
        except ExistingProjectError:
            return jsonify({'errormsg': f'Project with name {proj.name} already exists'}), 400

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_project(id: int) -> Tuple[Response, int]:
        """
        Gets single project from metadata repository
        :param id: id of project
        :return: Response with requested project or error
        """
        project = ebonite.meta_repo.get_project_by_id(id)
        if project:
            return jsonify({'project': pj.dumps(project)}), 200
        else:
            return jsonify({'errormsg': f'Project with id {id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_project(id: int) -> Tuple[Response, int]:
        """
        Changes name of project in metadata repository
        :param id: id of project
        :return: Response with code 204 or error
        """
        body = request.get_json(force=True)
        body['id'] = id
        proj = ProjectBody.from_data(body)
        try:
            ebonite.meta_repo.update_project(proj)
            return jsonify({}), 204
        except NonExistingProjectError:
            return jsonify({'errormsg': f'Project with id {id} does not exist'}), 400

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_project(id: int) -> Tuple[Response, int]:
        """
        Deletes either only project or cascadely deletes everything linked to it from metadata repository
        :param id: id of project
        :return: Response with code 204 or error
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        proj = ebonite.meta_repo.get_project_by_id(id)
        if not proj:
            return jsonify({'errormsg': f'Project with id {id} does not exist'}), 404
        if cascade:
            ebonite.delete_proj_cascade(proj)
            return jsonify({}), 204
        else:
            try:
                ebonite.meta_repo.delete_project(proj)
                return jsonify({}), 204
            except ProjectWithRelationshipError as e:
                return jsonify({'errormsg': str(e)}), 400

    return blueprint


def task_blueprint(ebonite):
    blueprint = Blueprint('tasks', __name__, url_prefix='/tasks')

    @blueprint.route('', methods=['GET'])
    def get_tasks() -> Tuple[Response, int]:
        """
        Get all tasks from metadata repository for given project
        :return: Response with all project for given project or error
        """
        proj_id = request.args.get('project_id')
        if proj_id and proj_id.isnumeric():
            proj = ebonite.meta_repo.get_project_by_id(int(proj_id))
            if proj:
                return jsonify({'tasks': [pj.dumps(ebonite.meta_repo.get_task_by_id(t)) for t in proj.tasks]}), 200
            else:
                return jsonify({'errormsg': f'Project with id {proj_id} is not found'}), 404
        else:
            return jsonify({'errormsg': 'You should provide valid project_id as URL parameter'}), 400

    @blueprint.route('', methods=['POST'])
    def create_task() -> Tuple[Response, int]:
        """
        Creates task in metadata repository
        :return: Response with created task or error
        """
        body = TaskBody.from_data(request.get_json(force=True))
        try:
            task = ebonite.meta_repo.create_task(body)
            return jsonify({'task': pj.dumps(task)}), 201
        except ExistingTaskError:
            # TODO: Returns even if task doesn't exist when project_id  does not belong to any project
            return jsonify({'errormsg': f'Task with name {body.name} already exists'}), 404

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_task(id: int) -> Tuple[Response, int]:
        """
        Gets task from metadata repository
        :param id: id of the task
        :return: Response with task or error
        """
        try:
            task = ebonite.meta_repo.get_task_by_id(id)
            return jsonify({'task': pj.dumps(task)}), 200
        except NonExistingTaskError:
            return jsonify({'errormsg': f'Task with id {id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_task(id: int) -> Tuple[Response, int]:
        """
        Changes name of task in metadata repository
        :param id: id of task
        :return: Response with 204 code or error
        """
        body = request.get_json(force=True)
        body['id'] = id
        task = TaskBody.from_data(body)
        try:
            ebonite.meta_repo.update_task(task)
            return jsonify({}), 204
        except NonExistingTaskError:
            return jsonify({'errormsg': f'Task with id {id} in project {body.project_id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_task(id: int) -> Tuple[Response, int]:
        """
        Deletes either only task or cascadely deletes everything linked to it from metadata repository
        :param id: id of task
        :return: Response with 204 code or error
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        task = ebonite.meta_repo.get_task_by_id(id)
        if not task:
            return jsonify({'erromsg': f'Task with id {id} does not exist'}), 404
        else:
            if cascade:
                ebonite.delete_task_cascade(task)
                return jsonify({}), 204
            else:
                try:
                    ebonite.meta_repo.delete_task(task)
                    return jsonify({}), 204
                except TaskWithRelationshipError as e:
                    return jsonify({'errormsg': str(e)}), 404

    return blueprint


def errors_blueprint(ebonite):
    blueprint = Blueprint('errors', __name__)

    @blueprint.app_errorhandler(Exception)
    def unknown_exception_handler(exception: Exception) -> Tuple[Response, int]:
        """
        Handles exceptions which aren't covered in methods or by another handlers
        :return: Response with error message
        """
        return jsonify({'errormsg': 'Unknown exception. Check if your request is structured according to the docs. '
                                    'If that does not help contact Ebonite development team '
                                    'or create an issue on projects github page'}), 520

    @blueprint.app_errorhandler(ValidationError)
    def validation_exception_handler(exception: ValidationError) -> Tuple[Response, int]:
        """
        Handles exception which occures during body validation in POST and UPDATE requests
        :return: Response with description of errors
        """
        return jsonify({'errormsg': exception.errors()}), 400

    return blueprint
