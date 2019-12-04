from ebonite import start_runtime
from ebonite.ext.flask import server

start_runtime()

app = server.current_app

__all__ = ['app']
