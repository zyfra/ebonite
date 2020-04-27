from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.api.helpers import EnvironmentIdValidator, ImageIdValidator
from ebonite.client.base import Ebonite
from ebonite.core.errors import ExistingInstanceError, NonExistingInstanceError
from ebonite.core.objects import RuntimeInstance


class RunInstanceBody(PyjacksonModel):
    __type__ = RuntimeInstance
    __autogen_nested__ = True
    __include__ = ['name', 'environment_id', 'image_id', 'params']
    __force_required__ = ['image_id', 'params']


class UpdateInstanceBiody(PyjacksonModel):
    __type__ = RuntimeInstance
    __autogen_nested__ = True
    __include__ = ['id', 'name']
    __force_required__ = ['id']


def instances_blueprint(ebonite: Ebonite):
    blueprint = Blueprint('instances', __name__, url_prefix='/instances')

    @blueprint.route('', methods=['GET'])
    def get_instances() -> Tuple[Response, int]:
        environment_id, image_id = request.args.get('environment_id'), request.args.get('image_id')
        env = image = None
        if environment_id:
            EnvironmentIdValidator(environment_id=environment_id)
            env = ebonite.meta_repo.get_environment_by_id(environment_id)
        if image_id:
            ImageIdValidator(image_id=image_id)
            image = ebonite.meta_repo.get_image_by_id(image_id)
        try:
            instances = ebonite.meta_repo.get_instances(image=image, environment=env)
            return jsonify([pj.dumps(x) for x in instances]), 200
        except ValueError as e:
            return jsonify({'errormsg': str(e)}), 404

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_instance(id: int) -> Tuple[Response, int]:
        instance = ebonite.meta_repo.get_instance_by_id(id)
        if instance:
            return jsonify(pj.dumps(instance)), 200
        else:
            return jsonify({'errormsg': f'Instance with id {id} does not exist'})

    @blueprint.route('', methods=['POST'])
    def run_instance() -> Tuple[Response, int]:
        instance = RunInstanceBody.from_data(request.get_json(force=True))
        image = ebonite.meta_repo.get_image_by_id(instance.image_id)
        env = ebonite.meta_repo.get_environment_by_id(instance.environment_id) if instance.environment_id else None
        if not image:
            return jsonify({'errormsg': f'Could not run instance. '
                                        f'Image with id {instance.image_id} does not exist'}), 404
        try:
            instance = ebonite.run_instance(name=instance.name, image=image, environment=env)
            return jsonify(pj.dumps(instance)), 201
        except ExistingInstanceError:
            return jsonify({'errormsg': f'Instance with name {instance.name} '
                                        f'and image {image.name} already exists'}), 400

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_instance(id: int) -> Tuple[Response, int]:
        body = request.get_json(force=True)
        body['id'] = id
        instance = UpdateInstanceBiody.from_data(body)
        try:
            ebonite.meta_repo.update_instance(instance)
            return jsonify({}), 204
        except NonExistingInstanceError:
            return jsonify({'errormsg': f'Instance with id {id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_instance(id: int) -> Tuple[Response, int]:
        instance = ebonite.meta_repo.get_instance_by_id(id)
        if not instance:
            return jsonify({'errormsg': f'Instance with id {id} does not exist'}), 404
        ebonite.stop_instance(instance)
        return jsonify({}), 204

    return blueprint
