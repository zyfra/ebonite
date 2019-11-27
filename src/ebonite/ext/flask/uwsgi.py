from ebonite import start_runtime
from ebonite.ext.flask.server import current_app as app

start_runtime()


__all__ = ['app']
