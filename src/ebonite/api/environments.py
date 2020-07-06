from typing import Tuple

from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.client.base import Ebonite
from ebonite.core.errors import EnvironmentWithInstancesError, ExistingEnvironmentError, NonExistingEnvironmentError
from ebonite.core.objects import RuntimeEnvironment
from ebonite.api.helpers import dumps_pj


class CreateEnvironmentBody(PyjacksonModel):
    __type__ = RuntimeEnvironment
    __autogen_nested__ = True
    __include__ = ['name', 'params']
    __force_required__ = ['params']


class UpdateEnvironmentBody(PyjacksonModel):
    __type__ = RuntimeEnvironment
    __autogen_nested__ = True
    __include__ = ['id', 'name']
    __force_required__ = ['id']


def environments_blueprint(ebonite: Ebonite):
    blueprint = Blueprint('environments', __name__, url_prefix='/environments')

    @blueprint.route('', methods=['GET'])
    def get_environments() -> Tuple[Response, int]:
        """
        Gets all environments from metadata repository
        ---
        responses:
          200:
            description: A list of tasks belonging to the project
        """
        return jsonify([dumps_pj(x) for x in ebonite.meta_repo.get_environments()]), 200

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_environment(id: int) -> Tuple[Response, int]:
        """
        Gets single environment by id
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Environment with given id
          404:
            description: Environment with given id does not exist
        """
        env = ebonite.meta_repo.get_environment_by_id(id)
        if env is not None:
            return jsonify(dumps_pj(env)), 200
        else:
            return jsonify({'errormsg': f'Environment with id {id} does not exist'}), 404

    @blueprint.route('', methods=['POST'])
    def create_environment() -> Tuple[Response, int]:
        """
        Create environment in metadata repository
        ---
        parameters:
          - name: body
            in: body
            required: true
            schema:
              required:
                - name
                - params
              properties:
                name:
                  description:
                    type: string
                    description: environment name
                params:
                  description: Environemnt params
                  schema:
                    properties:
                      host:
                        type: string
                      type:
                        type: string
        responses:
          200:
            description: Environment created successfully
            examples:
              new env: {
                "name": "first environment",
                "id": 1,
                "author": "user_name",
                "creation_date": "1970-01-01 00:00:00.000000 ",
                "params": {
                  "host": "localhost:1234",
                  "type": "ebonite.build.docker.DockerHost"
                }
              }
          400:
            description: Environment with given name already exist
        """
        env = CreateEnvironmentBody.from_data(request.get_json(force=True))
        try:
            env = ebonite.meta_repo.create_environment(env)
            return jsonify(dumps_pj(env)), 201
        except ExistingEnvironmentError:
            return jsonify({'errormsg': f'Environment with name {env.name} already exist'}), 400

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_environment(id: int) -> Tuple[Response, int]:
        """
        Updates environment name
        ---
        parameters:
          - name: id
            in: path
            description: environment id to be updated
            required: true
          - name: body
            in: body
            schema:
              required:
                - name
              properties:
                name:
                  description: New environment name
                  type: string
        responses:
          200:
            description: Environment updated successfully
          404:
            description: Environment with given id does not exist
        """
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
        """
        Deletes either only environment or cascadely deletes everything linked to it from metadata repository
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
            description: Environment succesfully deleted
          404:
            description: Environment with given id does not exist
          400:
            description: Environment has foreign key and could not be deleted not cascadely
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        env = ebonite.meta_repo.get_environment_by_id(id)
        if env is None:
            return jsonify({'errormsg': f'Environment with id {id} does not exist'}), 404
        try:
            ebonite.delete_environment(env, cascade=cascade)
            return jsonify({}), 204
        except EnvironmentWithInstancesError as e:
            return jsonify({'errormsg': str(e)}), 400

    return blueprint
