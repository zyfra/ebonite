from ebonite import config
from ebonite.client import Ebonite, create_model
from ebonite.ext.ext_loader import ExtensionLoader, load_extensions
from ebonite.runtime.command_line import start_runtime
from ebonite.utils.ebdebug import EBONITE_DEBUG

if config.Core.AUTO_IMPORT_EXTENSIONS:
    ExtensionLoader.load_all()
__all__ = ['load_extensions', 'Ebonite', 'EBONITE_DEBUG', 'start_runtime', 'create_model']
__version__ = '0.2.1'

if __name__ == '__main__':
    pass
