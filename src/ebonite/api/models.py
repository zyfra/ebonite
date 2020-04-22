from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.client.base import Ebonite
from ebonite.core.errors import ModelWithImagesError, NonExistingModelError
from ebonite.core.objects.core import Model


class GetModelsListBody(PyjacksonModel):
    __type__ = Model
    __exclude__ = ['id', 'name', 'author', 'creation_date',
                   'wrapper', 'artifact', 'requirements', 'description', 'params']
    __force_required__ = ['task_id']


class GetModelBody(PyjacksonModel):
    __type__ = Model
    __exclude__ = ['name', 'author', 'creation_date',
                   'wrapper', 'artifact', 'requirements', 'description', 'params', 'task_id']
    __force_required__ = ['id']


class UpdateModelBody(PyjacksonModel):
    __type__ = Model
    __exclude__ = ['author', 'creation_date',
                   'wrapper', 'artifact', 'requirements', 'description', 'params']
    __force_required__ = ['id', 'task_id', 'name']


def models_blueprint(ebonite: Ebonite) -> Blueprint:
    blueprint = Blueprint('models', __name__, url_prefix='/models')

    @blueprint.route('', methods=['GET'])
    def get_models() -> Tuple[Response, int]:
        body = GetModelsListBody.from_data(request.args)
        task = ebonite.meta_repo.get_task_by_id(body.task_id)
        if task:
            return jsonify([pj.dumps(ebonite.meta_repo.get_model_by_id(x)) for x in task.models]), 200
        else:
            return jsonify({'errormsg': f'Task with id {body.task_id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_model(id: int) -> Tuple[Response, int]:
        body = GetModelBody.from_data({'id': id})
        model = ebonite.meta_repo.get_model_by_id(body.id)
        if model:
            return jsonify(pj.dumps(model)), 200
        else:
            return jsonify({'errormsg': f'Model with id {body.id} does not exist'}), 404

    @blueprint.route('/<int:id>/artifacts/<str:name>', methods=['GET'])
    def get_model_artifacts(id: int, name: str):
        body = GetModelBody.from_data({'id': id})
        model = ebonite.meta_repo.get_model_by_id(body.id)
        if not model:
            return jsonify({'errormsg': f'Model with id {body.id} does not exist'}), 404
        artifacts = ebonite.artifact_repo.get_artifact(model)
        with artifacts.blob_dict() as blobs:
            artifact = blobs.get(name)
        if artifact:
            return jsonify(pj.dumps(artifact)), 200
        else:
            return jsonify({'errormsg': f'Artifact with name {name} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_model(id: int):
        body = request.get_json(force=True)
        body['id'] = id
        model = UpdateModelBody.from_data(body)
        try:
            ebonite.meta_repo.update_model(model)
            return jsonify({}), 204
        except NonExistingModelError:
            return jsonify({'errormsg': f'Model with id {id} and task_id {model.task_id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_model(id: int):
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        body = GetModelBody.from_data({'id': id})
        model = ebonite.meta_repo.get_model_by_id(body.id)
        if not model:
            return jsonify({'errormsg': f'Model with id {body.id} does not exist'}), 404
        try:
            ebonite.delete_model(model, True, cascade)
            return jsonify({}), 204
        except ModelWithImagesError as e:
            return jsonify({'errormsg': str(e)}), 400

    return blueprint
