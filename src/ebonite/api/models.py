from typing import Tuple

from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.api.helpers import TaskIdValidator, dumps_pj
from ebonite.client.base import Ebonite
from ebonite.core.errors import NonExistingModelError
from ebonite.core.objects.core import Model
from ebonite.repository.artifact.base import NoSuchArtifactError


class UpdateModelBody(PyjacksonModel):
    __type__ = Model
    __include__ = ['id', 'name', 'task_id']
    __force_required__ = ['id', 'task_id']


def models_blueprint(ebonite: Ebonite) -> Blueprint:
    blueprint = Blueprint('models', __name__, url_prefix='/models')

    @blueprint.route('', methods=['GET'])
    def get_models() -> Tuple[Response, int]:
        """
        Returns all models belonging to the task
        ---
        parameters:
          - name: task_id
            in: query
            type: integer
            required: true
        responses:
          200:
            description: A list of models belonging to the project
          404:
            description: Task with given id does not exist
        """
        task_id = request.args.get('task_id')
        TaskIdValidator(task_id=task_id)
        task = ebonite.meta_repo.get_task_by_id(task_id)
        if task is not None:
            return jsonify([dumps_pj(ebonite.meta_repo.get_model_by_id(x)) for x in task.models]), 200
        else:
            return jsonify({'errormsg': f'Task with id {task_id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_model(id: int) -> Tuple[Response, int]:
        """
        Get specific model by id
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Model by given id
          404:
            description: Model with given id does not exist
        """
        model = ebonite.meta_repo.get_model_by_id(id)
        if model is not None:
            return jsonify(dumps_pj(model)), 200
        else:
            return jsonify({'errormsg': f'Model with id {id} does not exist'}), 404

    @blueprint.route('/<int:id>/artifacts/<string:name>', methods=['GET'])
    def get_model_artifacts(id: int, name: str):
        """
        Gets artifact for selected model
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
          - name: name
            in: path
            type: string
            required: true
            description: name of the artifact ro be retrieved
        responses:
          200:
            description: Returns an artifact specified in path
          404:
            description: Model or artifact does not exist
        """
        model = ebonite.meta_repo.get_model_by_id(id)
        if model is None:
            return jsonify({'errormsg': f'Model with id {id} does not exist'}), 404
        try:
            artifacts = ebonite.artifact_repo.get_artifact(model)
        except NoSuchArtifactError:
            return jsonify({'errormsg': f'No artifacts for model with id {model.id}'})
        with artifacts.blob_dict() as blobs:
            artifact = blobs.get(name)
        if artifact is not None:
            return jsonify(dumps_pj(artifact)), 200
        else:
            return jsonify({'errormsg': f'Artifact with name {name} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_model(id: int):
        """
        Updates model in metadata repository
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
                - task_id
              properties:
                name:
                  type: string
                  description: New model name
                task_id:
                  type: integer
                  description: id of the task model belongs to
        responses:
          204:
            description: Model updated successfully
          404:
            description: Model or task with given ids does not exist
        """
        body = request.get_json(force=True)
        body['id'] = id
        model = UpdateModelBody.from_data(body)
        try:
            # TODO: It's ugly. Think about another way to deal with wrapper abscence
            model = ebonite.meta_repo.get_model_by_id(model.id)
            model.name = body['name']
            ebonite.meta_repo.update_model(model)
            return jsonify({}), 204
        except NonExistingModelError:
            return jsonify({'errormsg': f'Model with id {id} and task_id {model.task_id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_model(id: int):
        """
        Deletes model with given id
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          204:
            description: Model deleted successfully
          404:
            description: Model with given id does not exist
        """
        model = ebonite.meta_repo.get_model_by_id(id)
        model = ebonite.get_model(model.name, model.task)
        if model is None:
            return jsonify({'errormsg': f'Model with id {id} does not exist'}), 404
        ebonite.delete_model(model)
        return jsonify({}), 204

    return blueprint
