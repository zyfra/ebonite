# EBNT-142 too many Tensorflow deprecation warnings
def fix_warnings():  # noqa
    import logging  # noqa
    import warnings  # noqa
    logging.getLogger("tensorflow").setLevel(logging.CRITICAL)  # noqa
    warnings.filterwarnings('ignore', category=FutureWarning)  # noqa
    warnings.filterwarnings('ignore', category=DeprecationWarning)  # noqa
fix_warnings()  # noqa


from ebonite import config
from ebonite.client import Ebonite, create_model
from ebonite.ext.ext_loader import ExtensionLoader, load_extensions
from ebonite.runtime.command_line import start_runtime

EBONITE_DEBUG = config.Core.DEBUG
if config.Core.AUTO_IMPORT_EXTENSIONS:
    ExtensionLoader.load_all()

__all__ = ['load_extensions', 'Ebonite', 'EBONITE_DEBUG', 'start_runtime', 'create_model']
__version__ = '0.3.1'

if __name__ == '__main__':
    pass
