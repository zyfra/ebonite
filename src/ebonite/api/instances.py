from typing import Tuple, Union

from pyjackson import serialize, deserialize
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.api.errors import ObjectWithIdDoesNotExist
from ebonite.api.helpers import EnvironmentIdValidator, ImageIdValidator, InstanceUpdateValidator
from ebonite.client.base import Ebonite
from ebonite.core.errors import ExistingInstanceError
from ebonite.core.objects import RuntimeInstance
from ebonite.ext.docker.base import DockerImage, DockerRegistry


class RunInstanceBody(PyjacksonModel):
    __type__ = RuntimeInstance
    __autogen_nested__ = True
    __include__ = ['name', 'environment_id', 'image_id']
    __force_required__ = ['image_id']


class UpdateInstanceBiody(PyjacksonModel):
    __type__ = RuntimeInstance
    __autogen_nested__ = True
    __include__ = ['id', 'name']
    __force_required__ = ['id']


def instances_blueprint(ebonite: Ebonite):
    blueprint = Blueprint('instances', __name__, url_prefix='/instances')

    @blueprint.route('', methods=['GET'])
    def get_instances() -> Tuple[Response, int]:
        """
        Get instances
        ---
        parameters:
          - name: environment_id
            in: query
            type: integer
            required: false
          - name: image_id
            in: query
            type: integer
            required: false
        responses:
          200:
            description: List of instances belonging to image and environment provided.
          404:
            description: Returned if both parameters are abscent from request

        """
        environment_id, image_id = request.args.get('environment_id'), request.args.get('image_id')
        env = image = None
        if environment_id is not None:
            EnvironmentIdValidator(environment_id=environment_id)
            env = ebonite.meta_repo.get_environment_by_id(environment_id)
        if image_id is not None:
            ImageIdValidator(image_id=image_id)
            image = ebonite.meta_repo.get_image_by_id(image_id)
        try:
            instances = ebonite.get_instances(image=image, environment=env)
            return jsonify([serialize(x) for x in instances]), 200
        except ValueError as e:
            return jsonify({'errormsg': str(e)}), 404

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_instance(id: int) -> Tuple[Response, int]:
        """
        Get instance by id
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Successfully returned id
          404:
            description: Instance with given id does not exist
        """
        instance = ebonite.meta_repo.get_instance_by_id(id)
        if instance is not None:
            return jsonify(serialize(instance)), 200
        else:
            raise ObjectWithIdDoesNotExist('Instance', id)

    @blueprint.route('', methods=['POST'])
    def run_instance() -> Tuple[Response, int]:
        """
        Creates and runs instance
        ---
        parameters:
          - name: body
            in: body
            required: true
            schema:
              required:
                - instance
              properties:
                instance:
                  schema:
                    properties:
                      name:
                        type: string
                        description: Instance name
                        required: true
                      image_id:
                        type: integer
                        description: Id of an image to be run in container
                        required: true
                      environment_id:
                        type: integer
                        description: id of an environment(optional)
                        required: false
                runner_kwargs:
                  description: Dictionary representing parameters for runner
                  required: false
                instance_kwargs:
                  description: Dictionary representing parameters for instance
                  required: false
          - name: run
            in: query
            type: integer
            required: false
            default: 0
        responses:
          201:
            description: Instance successfully created
          400:
            description: Image with given name already exist
          404:
            description:


        """
        run = False if not request.args.get('run') else bool(int(request.args.get('run')))
        body = request.get_json(force=True)
        runner_kwargs = body.get('runner_kwargs')
        instance_kwargs = body.get('instance_kwargs', {})
        instance = RunInstanceBody.from_data(body.get('instance'))

        image = ebonite.meta_repo.get_image_by_id(instance.image_id)
        env = ebonite.meta_repo.get_environment_by_id(instance.environment_id) if instance.environment_id is not None\
            else None
        if image is None:
            raise ObjectWithIdDoesNotExist('Image', instance.image_id)
        try:
            instance = ebonite.create_instance(name=instance.name, image=image,
                                               environment=env, run=run, runner_kwargs=runner_kwargs, **instance_kwargs)
            return jsonify(serialize(instance)), 201
        except ExistingInstanceError:
            return jsonify({'errormsg': f'Instance with name {instance.name} '
                                        f'and image {image.name} already exists'}), 400
        except (ValueError, TypeError) as e:
            return jsonify({'errormsg': str(e)}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_instance(id: int) -> Union[Tuple[Response, int], Tuple[str, int]]:
        """
        Updates image stored in metaddata repository.
        Won't recreate instance - just updates it's representation in repo.
        ---

        """
        instance = ebonite.meta_repo.get_instance_by_id(id)
        if instance is None:
            raise ObjectWithIdDoesNotExist('Instance', id)
        body = request.get_json(force=True)
        body['id'] = id
        InstanceUpdateValidator(**body)
        params = registry = None
        params = body.pop('params', params)
        registry = params.pop('registry', registry)
        if params:
            params = deserialize(params, RuntimeInstance.Params)
            if registry:
                registry = deserialize(registry, DockerRegistry)
                params.registry = registry
        body['params'] = params
        instance = instance.update(body)
        ebonite.meta_repo.update_instance(instance)
        return '', 204


    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_instance(id: int) -> Union[Tuple[Response, int], Tuple[str, int]]:
        """
        Deletes and, optionally, stops instance
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
          - name: meta_only
            in: query
            type: integer
            required: false
            default: 0
        responses:
          204:
            description: Image succesfully deleted
          404:
            description: Image with given id does not exist
        """
        meta_only = False if not request.args.get('meta_only') else bool(int(request.args.get('meta_only')))
        instance = ebonite.meta_repo.get_instance_by_id(id)
        if instance is None:
            return jsonify({'errormsg': f'Instance with id {id} does not exist'}), 404
        ebonite.delete_instance(instance, meta_only=meta_only)
        return '', 204

    return blueprint
