# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['tailapi']

package_data = \
{'': ['*']}

install_requires = \
['magicattr', 'oreo @ git+https://github.com/syvlorg/oreo.git@main', 'requests']

setup_kwargs = {
    'name': 'tailapi',
    'version': '1.0.0.0',
    'description': 'A python application and library to interact with the tailscale api!',
    'long_description': None,
    'author': 'sylvorg',
    'author_email': 'jeet.ray@syvl.org',
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3.10,<3.11',
}


setup(**setup_kwargs)

