from typing import Tuple

from flask import Blueprint, Response, jsonify, request
from pyjackson.pydantic_ext import PyjacksonModel

from ebonite.api.helpers import dumps_pj
from ebonite.client.base import Ebonite
from ebonite.core.errors import ExistingProjectError, NonExistingProjectError, ProjectWithTasksError
from ebonite.core.objects.core import Project


class ProjectCreateBody(PyjacksonModel):
    __type__ = Project

    __include__ = ['name']


class ProjectUpdateBody(PyjacksonModel):
    __type__ = Project

    __include__ = ['id', 'name']
    __force_required__ = ['id']


def project_blueprint(ebonite: Ebonite) -> Blueprint:
    blueprint = Blueprint('projects', __name__, url_prefix='/projects')

    @blueprint.route('', methods=['GET'])
    def get_projects() -> Tuple[Response, int]:
        """Gets all projects from metadata repository
        ---
        responses:
          200:
            description: A list of projects stored in meta repository
            examples:
              None: [{'Project1': 'blabla'}, {'Project2': 'blabla2'}]
        """
        projects = ebonite.meta_repo.get_projects()
        return jsonify([dumps_pj(p) for p in projects]), 200

    @blueprint.route('', methods=['POST'])
    def create_project() -> Tuple[Response, int]:
        """
        Creates project in metadata repository
        :return: Response with created object or error
        """
        project = ProjectCreateBody.from_data(request.get_json(force=True))
        try:
            project = ebonite.meta_repo.create_project(project)
            return jsonify(dumps_pj(project)), 201
        except ExistingProjectError:
            return jsonify({'errormsg': f'Project with name {project.name} already exists'}), 400

    @blueprint.route('/<int:id>', methods=['GET'])
    def get_project(id: int) -> Tuple[Response, int]:
        """
        Gets single project from metadata repository
        :param id: id of project
        :return: Response with requested project or error
        """
        project = ebonite.meta_repo.get_project_by_id(id)
        if project is not None:
            return jsonify(dumps_pj(project)), 200
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
        project = ebonite.meta_repo.get_project_by_id(id)
        if project is None:
            return jsonify({'errormsg': f'Project with id {id} does not exist'}), 404
        try:
            ebonite.delete_project(project, cascade)
            return jsonify({}), 204
        except ProjectWithTasksError as e:
            return jsonify({'errormsg': str(e)}), 400

    return blueprint
