from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.core.errors import (ExistingTaskError, NonExistingTaskError,
                                 TaskWithRelationshipError)
from ebonite.core.objects.core import Task


class TaskBody(PyjacksonModel):
    __type__ = Task


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
