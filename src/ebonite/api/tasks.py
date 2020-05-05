from json import loads
from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.api.helpers import ProjectIdValidator
from ebonite.client.base import Ebonite
from ebonite.core.errors import ExistingTaskError, NonExistingTaskError, TaskWithModelsError
from ebonite.core.objects.core import Task


class TaskCreateBody(PyjacksonModel):
    __type__ = Task

    __include__ = ['name', 'project_id']
    __force_required__ = ['project_id']


class TaskUpdateBody(PyjacksonModel):
    __type__ = Task

    __include__ = ['id', 'name', 'project_id']
    __force_required__ = ['id', 'project_id']


def task_blueprint(ebonite: Ebonite) -> Blueprint:
    blueprint = Blueprint('tasks', __name__, url_prefix='/tasks')

    @blueprint.route('', methods=['GET'])
    def get_tasks() -> Tuple[Response, int]:
        """
        Get all tasks from metadata repository for given project
        :return: Response with all project for given project or error
        """
        project_id = request.args.get('project_id')
        ProjectIdValidator(project_id=project_id)
        project = ebonite.meta_repo.get_project_by_id(project_id)
        if project is not None:
            return jsonify([loads(pj.dumps(ebonite.meta_repo.get_task_by_id(t))) for t in project.tasks]), 200
        else:
            return jsonify({'errormsg': f'Project with id {project_id} does not exist'}), 404

    @blueprint.route('', methods=['POST'])
    def create_task() -> Tuple[Response, int]:
        """
        Creates task in metadata repository
        :return: Response with created task or error
        """
        task = TaskCreateBody.from_data(request.get_json(force=True))
        # TODO: Create specific error with handler to catch NonExistingObject
        project = ebonite.meta_repo.get_project_by_id(task.project_id)
        if project is None:
            return jsonify({'errormsg': f'Project with id {task.project_id} does not exist'}), 404
        try:
            task = ebonite.meta_repo.create_task(task)
            return jsonify(loads(pj.dumps(task))), 201
        except ExistingTaskError:
            return jsonify({'errormsg': f'Task with name {task.name} already exists'}), 404

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_task(id: int) -> Tuple[Response, int]:
        """
        Gets task from metadata repository
        :param id: id of the task
        :return: Response with task or error
        """
        task = ebonite.meta_repo.get_task_by_id(id)
        if task is not None:
            return jsonify(loads(pj.dumps(task))), 200
        else:
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
        task = TaskUpdateBody.from_data(body)
        if ebonite.meta_repo.get_task_by_id(task.project_id) is None:
            return jsonify({'errormsg': f'Project {task.project_id} does not exist'}), 404
        try:
            ebonite.meta_repo.update_task(task)
            return jsonify({}), 204
        except NonExistingTaskError:
            return jsonify({'errormsg': f'Task with id {task.id} in project {task.project_id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_task(id: int) -> Tuple[Response, int]:
        """
        Deletes either only task or cascadely deletes everything linked to it from metadata repository
        :param id: id of task
        :return: Response with 204 code or error
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        task = ebonite.meta_repo.get_task_by_id(id)
        if task is None:
            return jsonify({'erromsg': f'Task with id {id} does not exist'}), 404
        else:
            try:
                ebonite.delete_project(task, cascade)
                return jsonify({}), 204
            except TaskWithModelsError as e:
                return jsonify({'errormsg': str(e)}), 400

    return blueprint
