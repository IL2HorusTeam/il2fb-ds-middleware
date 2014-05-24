from setuptools import setup, find_packages

setup(
    name='il2ds-middleware',
    version='0.10.2',
    description='High-level access to IL-2 FB Dedicated Server.',
    license='GPLv2',
    url='https://github.com/IL2HorusTeam/il2ds-middleware',
    author='Alexander Oblovatniy',
    author_email='oblovatniy@gmail.com',
    packages=find_packages(exclude=["examples", ]),
    install_requires=[i.strip() for i in open("requirements.pip").readlines()],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: Free for non-commercial use',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries',
    ],
)
