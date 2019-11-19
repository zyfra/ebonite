#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, print_function

import io
import os
import re
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup

# allow setup.py to run from another directory
here = os.path.dirname(__file__)
here and os.chdir(here)


def read(*names, **kwargs):
    with io.open(
            join(dirname(__file__), *names),
            encoding=kwargs.get('encoding', 'utf8')
    ) as fh:
        return fh.read()


def get_requirements(file_name):
    return [r for r in read(file_name).split('\n') if r and not r.startswith('#')]


setup_args = dict(
    name='ebonite',
    version='0.2.1',
    license='Apache-2.0',
    description='Machine Learning Lifecycle Framework',
    long_description='%s\n%s' % (
        re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub('', read('README.rst')),
        re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst'))
    ),
    author='Mikhail Sveshnikov',
    author_email='mike0sv@gmail.com',
    url='https://github.com/zyfra/ebonite',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Utilities',
    ],
    project_urls={
        'Changelog': 'https://github.com/zyfra/ebonite/blob/master/CHANGELOG.rst',
        'Issue Tracker': 'https://github.com/zyfra/ebonite/issues',
    },
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    python_requires='>=3.6',
    install_requires=get_requirements('requirements.txt'),
    extras_require={
        # eg:
        #   'rst': ['docutils>=0.11'],
        #   ':python_version=="2.6"': ['argparse'],
        'testing': get_requirements('test.requirements.txt')
    },
    setup_requires=[
        'pytest-runner',
    ],
    entry_points={
        'console_scripts': [
            'ebnt = ebonite.cli:main',
        ]
    },
)

if __name__ == '__main__':
    setup(**setup_args)
