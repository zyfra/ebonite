from typing import Tuple, Union

from pyjackson import deserialize, serialize
from flask import Blueprint, Response, jsonify, request

from ebonite.api.errors import ObjectWithIdDoesNotExist
from ebonite.api.helpers import ImageUpdateValidator, TaskIdValidator, BuildableValidator
from ebonite.client.base import Ebonite
from ebonite.core.errors import (ExistingImageError, ImageWithInstancesError, NonExistingModelError,
                                 NonExistingPipelineError, NonExistingImageError)
from ebonite.core.objects import Image
from ebonite.core.objects.core import Buildable
from ebonite.ext.docker.base import DockerRegistry


def images_blueprint(ebonite: Ebonite) -> Blueprint:
    blueprint = Blueprint('images', __name__, url_prefix='/images')

    @blueprint.route('', methods=['GET'])
    def get_images() -> Tuple[Response, int]:
        """
        Gets images from metadata repository for given task
        ---
        parameters:
          - name: task_id
            in: query
            type: integer
            required: true
        responses:
          200:
            description: List of images belonging to the project
          404:
            description: Task with given id does not exist
        """
        task_id = request.args.get('task_id')
        TaskIdValidator(task_id=task_id)
        task = ebonite.meta_repo.get_task_by_id(task_id)
        if task is not None:
            return jsonify([serialize(x) for x in ebonite.get_images(task)]), 200
        else:
            raise ObjectWithIdDoesNotExist('Task', task_id)

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_image(id: int) -> Tuple[Response, int]:
        """
        Gets image bu given id
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Image from metadata repository
          404:
            description: Image with id does not exist
        """
        image = ebonite.meta_repo.get_image_by_id(id)
        if image is not None:
            return jsonify(serialize(image)), 200
        else:
            raise ObjectWithIdDoesNotExist('Image', id)

    @blueprint.route('', methods=['POST'])
    def build_image() -> Tuple[Response, int]:
        """
        Creates image in repository and optionally builds
        ---
        parameters:
          - name: body
            in: body
            required: true
            schema:
              required:
                - name
                - buildable
              properties:
                name:
                  type: string
                buildable:
                  schema:
                    properties:
                      type:
                        type: string
                        description: model or pipeline
                      model_id:
                        type: integer
                        description: id of buildable object

                builder_args:
                  description: dictionary with arguments for image build
          - name: skip_build
            in: query
            type: integer
            required: false
            default: 0
        responses:
          201:
            description: Image built successfully
          400:
            description: Image with given name already exist
          404:
            description: Either buildable with given id does not exist or there was an error with using
                         any of provided builder_args
        """
        skip_build = False if not request.args.get('skip_build') else bool(int(request.args.get('skip_build')))
        body = request.get_json(force=True)
        BuildableValidator(**body['buildable'])
        buildable = deserialize(body.pop('buildable'), Buildable)
        builder_args = None
        builder_args = body.pop('builder_args', builder_args)
        try:
            image = ebonite.create_image(buildable, name=body['name'], builder_args=builder_args, skip_build=skip_build)
            return jsonify(serialize(image)), 201
        except ExistingImageError:
            return jsonify({'errormsg': f'Image with name {body["name"]} already exists'}), 400
        except (ValueError, TypeError, NonExistingPipelineError, NonExistingModelError) as e:
            return jsonify({'errormsg': str(e)}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_image(id: int) -> Union[Tuple[Response, int], Tuple[str, int]]:
        """
        Updates image in repository.
        It does not recreate image, just updates it's representation in metadata repository
        ---
        parameters:
         - name: id
           in: path
           required: true
           type: integer
         - name: body
           in: body
           required: true
           schema:
             required:
               - task_id


        """
        body = request.get_json(force=True)
        body['id'] = id
        ImageUpdateValidator(**body)
        image = ebonite.meta_repo.get_image_by_id(id)
        if image is None:
            raise ObjectWithIdDoesNotExist('Image', id)

        buildable = body.pop('buildable', None)
        params = body.pop('params', None)
        if buildable:
            buildable = deserialize(buildable, Buildable)
            body['source'] = buildable
        if params:
            registry = params.pop('registry', None)
            params = deserialize(params, Image.Params)
            if registry:
                registry = deserialize(registry, DockerRegistry)
                params.registry = registry
            body['params'] = params
        image = image.update(body)
        ebonite.meta_repo.update_image(image)
        return '', 204

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_image(id: int) -> Union[Tuple[Response, int], Tuple[str, int]]:
        """
        Deletes either only image or cascadely deletes instances linked to it from metadata repository
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
          400:
            description: Image has foreign key and could not be deleted not cascadely
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        meta_only = False if not request.args.get('meta_only') else bool(int(request.args.get('meta_only')))
        image = ebonite.meta_repo.get_image_by_id(id)
        if image is None:
            raise ObjectWithIdDoesNotExist('Image', id)
        try:
            ebonite.delete_image(image, meta_only=meta_only, cascade=cascade)
            return '', 204
        except ImageWithInstancesError as e:
            return jsonify({'errormsg': str(e)}), 400

    return blueprint
