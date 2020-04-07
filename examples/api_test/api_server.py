from ebonite.api.api_base import EboniteApi
import os

os.environ['S3_ACCESS_KEY'] = 'eboniteAccessKey'
os.environ['S3_SECRET_KEY'] = 'eboniteSecretKey'

api = EboniteApi(name='test',config_path='client_config.json')
api.run()