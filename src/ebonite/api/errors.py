from typing import Tuple

from flask import Blueprint, Response, jsonify
from pydantic import ValidationError


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
        Handles exception which occures during body validation in POST and UPDATE requests
        :return: Response with description of errors
        """
        return jsonify({'errormsg': exception.errors()}), 400

    return blueprint
