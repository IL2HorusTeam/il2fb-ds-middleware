# coding: utf-8

import os

from setuptools import setup


__here__ = os.path.abspath(os.path.dirname(__file__))


def split_requirements(lines):
    requirements, dependencies = [], []

    for line in lines:
        if line.startswith('-e'):
            line = line.split(' ', 1)[1]
            dependencies.append(line)
            line = line.split('#egg=', 1)[1]

        requirements.append(line)

    return requirements, dependencies


with open(os.path.join(__here__, 'requirements', 'dist.txt')) as f:
    REQUIREMENTS = [x.strip() for x in f]
    REQUIREMENTS = [x for x in REQUIREMENTS if x and not x.startswith('#')]
    REQUIREMENTS, DEPENDENCIES = split_requirements(REQUIREMENTS)


README = open(os.path.join(__here__, 'README.rst')).read()


setup(
    name='il2fb-ds-middleware',
    version='1.0.0',
    description="High-level access to IL-2 FB Dedicated Server",
    license='GPLv2',
    url='https://github.com/IL2HorusTeam/il2fb-ds-middleware',
    author='Alexander Oblovatniy',
    author_email='oblovatniy@gmail.com',
    packages=[
        'il2fb.ds.middleware',
        'il2fb.ds.middleware.console',
        'il2fb.ds.middleware.device_link',
    ],
    namespace_packages=[
        'il2fb',
        'il2fb.ds',
    ],
    include_package_data=True,
    install_requires=REQUIREMENTS,
    dependency_links=DEPENDENCIES,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: Free for non-commercial use',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Natural Language :: English',
        "Operating System :: Unix",
        "Operating System :: Microsoft :: Windows",
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',
    ],
)
