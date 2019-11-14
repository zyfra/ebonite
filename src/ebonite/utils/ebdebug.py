import os

# from ebonite.utils.thread_watcher import watch_all_threads

EBONITE_DEBUG = os.environ.get('EBONITE_DEBUG', 'False') == 'True'
EBONITE_WATCH = os.environ.get('EBONITE_WATCH', 'False') == 'True'
EBONITE_WATCH_MODULES = os.environ.get('EBONITE_WATCH_MODULES', 'ebonite').split(',')

# if EBONITE_WATCH:
#     watch_all_threads(code_path_prefixes=EBONITE_WATCH_MODULES)
