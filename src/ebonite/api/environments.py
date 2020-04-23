from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.client.base import Ebonite
from ebonite.core.errors import EnvironmentWithInstancesError, ExistingEnvironmentError, NonExistingEnvironmentError
from ebonite.core.objects import RuntimeEnvironment


class CreateEnvironmentBody(PyjacksonModel):
    __type__ = RuntimeEnvironment

    __exclude__ = ['id', 'author', 'creation_date']
    __force_required__ = ['params']


class UpdateEnvironmentBody(PyjacksonModel):
    __type__ = RuntimeEnvironment

    __exclude__ = ['author', 'creation_date', 'params']
    __force_required__ = ['id']


def environments_blueprint(ebonite: Ebonite):
    blueprint = Blueprint('environments', __name__, url_prefix='/environments')

    @blueprint.route('', methods=['GET'])
    def get_environments() -> Tuple[Response, int]:
        return jsonify([pj.dumps(x) for x in ebonite.meta_repo.get_environments()]), 200

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_environment(id: int) -> Tuple[Response, int]:
        env = ebonite.meta_repo.get_environment_by_id(id)
        if env:
            return jsonify(pj.dumps(env)), 200
        else:
            return jsonify({'errormsg': f'Environment with id {id} does not exist'}), 404

    @blueprint.route('', methods=['POST'])
    def create_environment() -> Tuple[Response, int]:
        env = CreateEnvironmentBody.from_data(request.get_json(force=True))
        try:
            env = ebonite.meta_repo.create_environment(env)
            return jsonify(pj.dumps(env)), 201
        except ExistingEnvironmentError:
            return jsonify({'errormsg': f'Environment with name {env.name} already exist'}), 400

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_environment(id: int) -> Tuple[Response, int]:
        body = request.get_json(force=True)
        body['id'] = id
        env = UpdateEnvironmentBody.from_data(body)
        try:
            ebonite.meta_repo.update_environment(env)
            return jsonify({}), 204
        except NonExistingEnvironmentError:
            return jsonify({'errormsg': f'Environment with id {id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_environment(id: int) -> Tuple[Response, int]:
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        env = ebonite.meta_repo.get_environment_by_id(id)
        if not env:
            return jsonify()
        try:
            ebonite.delete_environment(env, cascade=cascade)
            return jsonify({}), 204
        except EnvironmentWithInstancesError as e:
            return jsonify({'errormsg': str(e)}), 400

    return blueprint
