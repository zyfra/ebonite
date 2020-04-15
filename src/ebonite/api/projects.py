from typing import Tuple

import pyjackson as pj
from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel

from ebonite.core.errors import ExistingProjectError, NonExistingProjectError, ProjectWithRelationshipError
from ebonite.core.objects.core import Project


class ProjectBody(BaseModel):
    name: str


def project_blueprint(ebonite):
    blueprint = Blueprint('projects', __name__, url_prefix='/projects')

    @blueprint.route('', methods=['GET'])
    def get_projects() -> Tuple[Response, int]:
        """
        Gets all projects from metadata repository
        :return: All projects in database
        """
        projects = ebonite.meta_repo.get_projects()
        return jsonify({'projects': [pj.dumps(p) for p in projects]}), 200

    @blueprint.route('', methods=['POST'])
    def create_project() -> Tuple[Response, int]:
        """
        Creates project in metadata repository
        :return: Response with created object or error
        """
        proj = ProjectBody(**request.get_json(force=True))
        proj = Project(name=proj.name)
        try:
            proj = ebonite.meta_repo.create_project(proj)
            return jsonify({'project': pj.dumps(proj)}), 201
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
            return jsonify({'project': pj.dumps(project)}), 200
        else:
            return jsonify({'errormsg': f'Project with id {id} does not exist'}), 404

    @blueprint.route('/<int:id>', methods=['PATCH'])
    def update_project(id: int) -> Tuple[Response, int]:
        """
        Changes name of project in metadata repository
        :param id: id of project
        :return: Response with code 204 or error
        """
        body = ProjectBody(**request.get_json(force=True))
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
        if cascade:
            ebonite.delete_proj(proj, cascade)
            return jsonify({}), 204
        else:
            try:
                ebonite.meta_repo.delete(proj)
                return jsonify({}), 204
            except ProjectWithRelationshipError as e:
                return jsonify({'errormsg': str(e)}), 400

    return blueprint
