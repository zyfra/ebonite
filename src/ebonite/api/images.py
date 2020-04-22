from typing import Tuple
import pyjackson as pj
from flask import Blueprint, jsonify, request, Response
from ebonite.client.base import Ebonite
from ebonite.core.errors import ImageWithInstancesError, NonExistingImageError
from pyjackson.pydantic_ext import PyjacksonModel
from ebonite.core.objects import Image


class GetImagesForModelBody(PyjacksonModel):
    __type__ = Image

    __force_required__ = ['model_id']
    __exclude__ = ['id', 'name', 'author', 'creation_date', 'params']


class GetImageBody(PyjacksonModel):
    __type__ = Image

    __force_required__ = ['id']
    __exclude__ = ['name', 'author', 'creation_date', 'params', 'model_id']


class BuildImageBody(PyjacksonModel):
    __type__ = Image

    __force_required__ = ['name', 'model_id']
    __exclude__ = ['id', 'author', 'creation_date', 'params']


class UpdateImageBody(PyjacksonModel):
    __type__ = Image

    __force_required__ = ['id', 'name', 'model_id']
    __exclude__ = ['author', 'creation_date', 'params']


def images_blueprint(ebonite: Ebonite):
    blueprint = Blueprint('images', __name__, url_prefix='/images')

    @blueprint.route('', methods=['GET'])
    def get_images() -> Tuple[Response, int]:
        return

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_image(id: int) -> Tuple[Response, int]:
        return

    @blueprint.route('', methods=['POST'])
    def build_image():
        return

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_image(id: int):
        return

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_image(id: int):
        return