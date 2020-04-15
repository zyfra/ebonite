from typing import Tuple

from flask import Blueprint, Response, jsonify
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, NotFound


def errors_blueprint(ebonite):
    blueprint = Blueprint('errors', __name__)

    @blueprint.app_errorhandler(Exception)
    def unknown_exception_handler(exception: Exception) -> Tuple[Response, int]:
        """
        Handles exceptions which aren't covered in methods or by another handlers
        :return: Response with error message
        """
        return jsonify({'errormsg': 'Unknown exception. Check if your request is structured according to the docs. '
                                    'If that does not help contact Ebonite development team '
                                    'or create an issue on projects github page'}), 520

    @blueprint.app_errorhandler(ValidationError)
    def validation_exception_handler(exception: ValidationError) -> Tuple[Response, int]:
        """
        Handles exception which occures during body and param validation in requests
        :return: Response with description of errors
        """
        return jsonify({'errormsg': exception.errors()}), 400

    @blueprint.app_errorhandler(NotFound)
    def not_found_exception_handler(exception: NotFound):
        return jsonify({'errormsg':'The requested URL was not found on the server. '
                                   'If you entered the URL manually please check your spelling and try again'}), 404

    @blueprint.app_errorhandler(BadRequest)
    def bad_request_exception_handler(exception: BadRequest):
        return jsonify({'errormsg':'Bad Request'}), 404

    return blueprint
