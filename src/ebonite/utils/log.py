import logging.config
import os

LOG_LEVEL_NAME = os.environ.get('EBONITE_LOG_LEVEL', 'INFO')
LOG_LEVEL = logging._nameToLevel.get(LOG_LEVEL_NAME, logging.DEBUG)

logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': LOG_LEVEL,
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'ebonite': {
            'handlers': ['default'],
            'level': LOG_LEVEL,
        },
        'ebonite_runtime': {
            'handlers': ['default'],
            'level': LOG_LEVEL
        }
    }
}

logging.config.dictConfig(logging_config)

logger = logging.getLogger('ebonite')
rlogger = logging.getLogger('ebonite_runtime')
