from setuptools import setup, find_packages

setup(
    name='il2ds-middleware',
    version='0.5.3',
    description='High-level access to IL-2 FB Dedicated Server.',
    long_description=open('README.md').read(),
    license='MIT',
    url='https://github.com/IL2HorusTeam/il2ds-middleware',
    author='Alexander Oblovatniy',
    author_email='oblovatniy@gmail.com',
    packages=find_packages(),
    install_requires=[i.strip() for i in open("requirements.pip").readlines()],
    classifiers = [
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries',
    ],
)
