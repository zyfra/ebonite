from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel

from ebonite.core.errors import ExistingTaskError, NonExistingTaskError, TaskWithRelationshipError
from ebonite.core.objects.core import Task


class GetTaskBody(BaseModel):
    project_id: int


class TaskBody(GetTaskBody):
    name: str


def task_blueprint(ebonite):
    blueprint = Blueprint('tasks', __name__, url_prefix='/tasks')

    @blueprint.route('', methods=['GET'])
    def get_tasks() -> Tuple[Response, int]:
        """
        Get all tasks from metadata repository for given project
        :return: Response with all project for given project or error
        """
        proj_id = request.args.get('project_id')
        task = GetTaskBody(project_id=proj_id)
        proj = ebonite.meta_repo.get_project_by_id(task.project_id)
        if proj:
            return jsonify({'tasks': [pj.dumps(ebonite.meta_repo.get_task_by_id(t)) for t in proj.tasks]}), 200
        else:
            return jsonify({'errormsg': f'Project with id {proj_id} is not found'}), 404

    @blueprint.route('', methods=['POST'])
    def create_task() -> Tuple[Response, int]:
        """
        Creates task in metadata repository
        :return: Response with created task or error
        """
        body = TaskBody(**request.get_json(force=True))
        task = Task(name=body.name, project_id=body.project_id)
        try:
            task = ebonite.meta_repo.create_task(task)
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
        body = TaskBody(**body)
        task = Task(id=id,project_id=body.project_id,name=body.name)
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
            try:
                ebonite.delete_project(task, cascade)
                return jsonify({}), 204
            except TaskWithRelationshipError as e:
                return jsonify({'errormsg': str(e)}), 404

    return blueprint
