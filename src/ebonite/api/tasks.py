from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.api.helpers import ProjectIdValidator
from ebonite.client.base import Ebonite
from ebonite.core.errors import ExistingTaskError, NonExistingTaskError, TaskWithFKError
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
        ---
        parameters:
          - name: project_id
            in: query
            type: integer
            required: true
        responses:
          200:
            description: A list of tasks belonging to the project
            examples:
              /tasks?project_id=1:   [
                    {
                      "name": "first project",
                      "id": 1,
                      "author": "user_name",
                      "creation_date": "1970-01-01 00:00:00.000000 "
                    }
                  ]
        """
        project_id = request.args.get('project_id')
        ProjectIdValidator(project_id=project_id)
        project = ebonite.meta_repo.get_project_by_id(project_id)
        if project is not None:
            return jsonify([pj.serialize(ebonite.meta_repo.get_task_by_id(t)) for t in project.tasks]), 200
        else:
            return jsonify({'errormsg': f'Project with id {project_id} does not exist'}), 404

    @blueprint.route('', methods=['POST'])
    def create_task() -> Tuple[Response, int]:
        """
        Creates task in metadata repository
        ---
        parameters:
          - name: body
            in: body
            required: true
            schema:
              required:
                - name
                - project_id
              properties:
                name:
                  type: string
                  description: Task name.
                project_id:
                  type: integer
                  description: id of the project task belongs to
        responses:
          201:
            description: Task created succesfully
          404:
            description: Project with given id does not exist or task with given name already exist
        """
        task = TaskCreateBody.from_data(request.get_json(force=True))
        project = ebonite.meta_repo.get_project_by_id(task.project_id)
        if project is None:
            return jsonify({'errormsg': f'Project with id {task.project_id} does not exist'}), 404
        try:
            task = ebonite.meta_repo.create_task(task)
            return jsonify(pj.serialize(task)), 201
        except ExistingTaskError:
            return jsonify({'errormsg': f'Task with name {task.name} already exists'}), 404

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_task(id: int) -> Tuple[Response, int]:
        """
        Gets task from metadata repository
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Returns a task with id specified in path
            examples:
              /tasks/1:    {
                    "name": "first task",
                    "id": 1,
                    "project_id": 1,
                    "author": "user_name",
                    "creation_date": "1970-01-01 00:00:00.000000 "
                  }
          404:
            description: Task with given id does not exist
        """
        task = ebonite.meta_repo.get_task_by_id(id)
        if task is not None:
            return jsonify(pj.serialize(task)), 200
        else:
            return jsonify({'errormsg': f'Task with id {id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_task(id: int) -> Tuple[Response, int]:
        """
        Changes name of task in metadata repository
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
          - name: body
            in: body
            required: true
            schema:
              required:
                - name
                - project_id
              properties:
                name:
                  type: string
                  description: new name of the task
                project_id:
                  type: integer
                  description: id of the project to which task belongs
        responses:
          204:
            description: Returns a task with id specified in path
        404:
            description: Project or task in given project does not exist
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
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
          - name: cascade
            in: query
            type: integer
            required: false
            default: 0
        responses:
          204:
            description: Task succesfully deleted
          404:
            description: Task with given id does not exist
          400:
            description: Task has foreign key and could not be deleted not cascadely
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        task = ebonite.meta_repo.get_task_by_id(id)
        if task is None:
            return jsonify({'errormsg': f'Task with id {id} does not exist'}), 404
        else:
            try:
                ebonite.delete_task(task, cascade)
                return jsonify({}), 204
            except TaskWithFKError as e:
                return jsonify({'errormsg': str(e)}), 400

    return blueprint
