from flasgger import Swagger, swag_from
from flask import Flask, jsonify

app = Flask(__name__)
Swagger(app)


@app.route('/', methods=['GET'])
@swag_from({'responses': {'200': {'content': {'application/json': {'schema': {
    'type': 'object', 'properties': {'hello': {'type': 'string'}}}}}}}})
def hello():
    return jsonify({'hello': 'world'}), 200


__all__ = ['app']
