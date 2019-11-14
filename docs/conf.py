# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys

sys.path.insert(0, os.path.abspath('../src'))

extensions = [
    'sphinxcontrib.apidoc',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]
if os.getenv('SPELLCHECK'):
    extensions += 'sphinxcontrib.spelling',
    spelling_show_suggestions = True
    spelling_lang = 'en_US'

source_suffix = '.rst'
master_doc = 'index'
project = 'Ebonite'
year = '2019'
author = 'Mikhail Sveshnikov'
copyright = '{0}, {1}'.format(year, author)
version = release = '0.2.0'

pygments_style = 'trac'
templates_path = ['.']
extlinks = {
    'issue': ('https://github.com/zyfra/ebonite/issues/%s', '#'),
    'pr': ('https://github.com/zyfra/ebonite/pull/%s', 'PR #'),
}
import sphinx_rtd_theme

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
# html_theme_options = {
#     'githuburl': 'https://github.com/zyfra/ebonite/'
# }

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_sidebars = {
    '**': ['searchbox.html', 'globaltoc.html', 'sourcelink.html'],
}
html_short_title = '%s-%s' % (project, version)

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False

apidoc_module_dir = '../src/ebonite'
apidoc_output_dir = 'reference'

apidoc_excluded_paths = [
    '*/base.py',
    '*/helpers.py',
    'build/provider/*',
    'core/objects/artifacts',
    'core/objects/core',
    'core/objects/dataset_type',
    'core/objects/requirements',
    'core/objects/wrapper',
]

apidoc_toc_file = False
apidoc_module_first = True
apidoc_separate_modules = True
apidoc_extra_args = ['-d 2']

autodoc_member_order = 'bysource'
