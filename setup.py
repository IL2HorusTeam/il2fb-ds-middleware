from setuptools import setup, find_packages

install_requires = []

setup(
    name='IL2ServerConnector',
    version='0.0.1',
    description='High-level access to IL-2 FB Dedicated Server.',
    long_description=open('README.md').read(),
    license='MIT',
    url='https://github.com/IL2HorusTeam/server-connector',
    bugtrack_url='https://github.com/IL2HorusTeam/server-connector/issues',
    author='Alexander Oblovatniy',
    author_email='oblovatniy@gmail.com',
    packages=find_packages(),
    test_suite='il2_server_connector.tests',
    scripts=[],
    install_requires=install_requires,
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: MIT',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: PyPy',
        'Topic :: Software Development :: IL-2 FB DS'
    ],
)
