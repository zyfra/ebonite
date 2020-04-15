from typing import Tuple

from flask import Blueprint, Response, jsonify

from ebonite.build.docker import is_docker_running
from ebonite.repository.artifact.base import NoSuchArtifactError


def healthcheck_blueprint(ebonite):
    blueprint = Blueprint('healthcheks', __name__, url_prefix='/healthchecks')

    @blueprint.route('/docker', methods=['GET'])
    def docker_healthcheck() -> Tuple[Response, int]:
        """
        Checks if Docker daemon is ready to use
        :return: Response object which signifies if daemon is healthy
        """
        if is_docker_running():
            return jsonify({'msg': 'Docker daemon is healthy'}), 200
        else:
            return jsonify({'errormsg': 'Failed to establish connection to docker daemon'}), 404

    @blueprint.route('/metadata', methods=['GET'])
    def metadata_healthcheck() -> Tuple[Response, int]:
        """
        Checks if metadata repository is healthy by trying to get any project from it
        :return: Response object which signifies if metadata repository is healthy
        """
        try:
            ebonite.meta_repo.get_project_by_id(1)
            return jsonify({'msg': 'Metadata repository is healthy'}), 200
        except Exception as e:
            return jsonify({'errormsg': f'Error {e} while trying to establish connection to metadata repository'}), 404

    @blueprint.route('/artifact', methods=['GET'])
    def artifact_healthcheck() -> Tuple[Response, int]:
        """
        Checks if artifact repository is healthy by trying to get any artifact from it.
        Might return NoSuchArtifactError which signifies that repository is ready to use
        :return:  Response object which signifies if artifact repository is healthy
        """
        try:
            ebonite.artifact_repo._get_artifact('1')
            return jsonify({'msg': 'Artifact repository is healthy'}), 200
        except NoSuchArtifactError:
            return jsonify({'msg': 'Artifact repository is healthy'}), 200
        except Exception as e:
            return jsonify({'errormsg': f'Error {e} while trying to establish connection to artifact repository'}), 404

    return blueprint
