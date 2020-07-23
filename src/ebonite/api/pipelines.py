from typing import Tuple, Union

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.api.errors import ObjectWithIdDoesNotExist
from ebonite.api.helpers import TaskIdValidator
from ebonite.client.base import Ebonite
from ebonite.core.objects.core import Pipeline


class UpdatePipelineModel(PyjacksonModel):
    __type__ = Pipeline
    __autogen_nested__ = True
    __include__ = ['id', 'name', 'author', 'steps', 'input_data', 'output_data', 'task_id']
    __force_required__ = ['task_id']


def pipelines_blueprint(ebonite: Ebonite):
    blueprint = Blueprint('pipelines', __name__, url_prefix='/pipelines')

    @blueprint.route('', methods=['GET'])
    def get_pipelines() -> Tuple[Response, int]:
        """
        Gets pipelines for given task
        ---
        parameters:
          - name: task_id
            in: query
            type: integer
            description: Id of the task for which pipelines meant to be retrieved
        responses:
          200:
            description: List of pipelines for given task
          404:
            description: Task with given id does not exist
        """
        task_id = request.args.get('task_id')
        TaskIdValidator(task_id=task_id)
        task = ebonite.meta_repo.get_task_by_id(task_id)
        if task is not None:
            return jsonify([pj.serialize(x) for x in ebonite.get_pipelines(task)]), 200
        else:
            raise ObjectWithIdDoesNotExist('Task', task_id)

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_pipeline(id: int) -> Tuple[Response, int]:
        """
        Get pipeline with given id from metadata repository
        ---
        parameters:
          - name: id
            in: path
            type: integer
            description: Id of the pipeline meant to be retrieved
        responses:
          200:
            description: Pipeline with given id
          404:
            description: Pipeline with given id doesn't exist
        """
        pipeline = ebonite.meta_repo.get_pipeline_by_id(id)
        if pipeline is not None:
            return jsonify(pj.serialize(pipeline)), 200
        else:
            raise ObjectWithIdDoesNotExist('Pipeline', id)

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_pipeline(id: int):
        """
        Updates pipeline
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
                - task_id
              properties:
                name:
                  type: string
                  required: false
                  description:
        """
        body = request.get_json(force=True)
        body['id'] = id
        old_pipeline = ebonite.meta_repo.get_pipeline_by_id(id)
        if old_pipeline is None:
            raise ObjectWithIdDoesNotExist('Pipeline', id)
        # TODO: Should I leave options for this fields to be set through API?
        #  Need to think about representing complicated objects in dict.
        #  Adding methods to get dict representation for everything related to core and backwards?
        #  Including inner stuff?
        if body.get('steps') is None:
            body['steps'] = [x.__dict__ for x in old_pipeline.steps]
        if body.get('input_data') is None:
            body['input_data'] = old_pipeline.input_data.__dict__
        if body.get('output_data') is None:
            body['output_data'] = old_pipeline.output_data.__dict__
        pipeline = UpdatePipelineModel.from_data(body)
        ebonite.meta_repo.update_pipeline(pipeline)
        return '', 204

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_pipeline(id: int) -> Union[Tuple[Response, int], Tuple[str, int]]:
        """
        Deletes pipeline with given id
        ---
        parameters:
          - name: id
            in: path
            type: integer
            description: Id of the pipeline meant to be deleted
        responses:
          204:
            description: Pipeline delted successfully
          404:
            description:
        """
        pipeline = ebonite.meta_repo.get_pipeline_by_id(id)
        if pipeline is not None:
            ebonite.delete_pipeline(pipeline)
            return '', 204
        else:
            raise ObjectWithIdDoesNotExist('Pipeline', id)

    return blueprint
