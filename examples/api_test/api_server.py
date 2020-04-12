import os

from ebonite.api.api_base import EboniteAPI

os.environ['S3_ACCESS_KEY'] = 'eboniteAccessKey'
os.environ['S3_SECRET_KEY'] = 'eboniteSecretKey'

api = EboniteAPI(name='ebonite', config_path='client_config.json')
api.run()
