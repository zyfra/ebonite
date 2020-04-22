from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.client.base import Ebonite
from ebonite.core.errors import ExistingProjectError, NonExistingProjectError, ProjectWithTasksError
from ebonite.core.objects.core import Project


class ProjectCreateBody(PyjacksonModel):
    __type__ = Project

    __exclude__ = ['creation_date', 'author', 'id']


class ProjectUpdateBody(PyjacksonModel):
    __type__ = Project

    __exclude__ = ['creation_date', 'author']
    __force_required__ = ['id']


def project_blueprint(ebonite: Ebonite) -> Blueprint:
    blueprint = Blueprint('projects', __name__, url_prefix='/projects')

    @blueprint.route('', methods=['GET'])
    def get_projects() -> Tuple[Response, int]:
        """
        Gets all projects from metadata repository
        :return: All projects in database
        """
        projects = ebonite.meta_repo.get_projects()
        return jsonify([pj.dumps(p) for p in projects]), 200

    @blueprint.route('', methods=['POST'])
    def create_project() -> Tuple[Response, int]:
        """
        Creates project in metadata repository
        :return: Response with created object or error
        """
        proj = ProjectCreateBody.from_data(request.get_json(force=True))
        try:
            proj = ebonite.meta_repo.create_project(proj)
            return jsonify(pj.dumps(proj)), 201
        except ExistingProjectError:
            return jsonify({'errormsg': f'Project with name {proj.name} already exists'}), 400

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_project(id: int) -> Tuple[Response, int]:
        """
        Gets single project from metadata repository
        :param id: id of project
        :return: Response with requested project or error
        """
        project = ebonite.meta_repo.get_project_by_id(id)
        if project:
            return jsonify(pj.dumps(project)), 200
        else:
            return jsonify({'errormsg': f'Project with id {id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_project(id: int) -> Tuple[Response, int]:
        """
        Changes name of project in metadata repository
        :param id: id of project
        :return: Response with code 204 or error
        """
        body = request.get_json(force=True)
        body['id'] = id
        body = ProjectUpdateBody.from_data(body)
        try:
            ebonite.meta_repo.update_project(Project(name=body.name, id=id))
            return jsonify({}), 204
        except NonExistingProjectError:
            return jsonify({'errormsg': f'Project with id {id} does not exist'}), 400

    @blueprint.route('/<int:id>', methods=['DELETE'])
    def delete_project(id: int) -> Tuple[Response, int]:
        """
        Deletes either only project or cascadely deletes everything linked to it from metadata repository
        :param id: id of project
        :return: Response with code 204 or error
        """
        cascade = False if not request.args.get('cascade') else bool(int(request.args.get('cascade')))
        proj = ebonite.meta_repo.get_project_by_id(id)
        if not proj:
            return jsonify({'errormsg': f'Project with id {id} does not exist'}), 404
        try:
            ebonite.delete_project(proj, cascade)
            return jsonify({}), 204
        except ProjectWithTasksError as e:
            return jsonify({'errormsg': str(e)}), 400

    return blueprint
