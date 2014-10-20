from setuptools import setup

import versioneer
versioneer.VCS = 'git'
versioneer.versionfile_source = 'eliot/_version.py'
versioneer.versionfile_build = 'eliot/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = 'eliot-'


def read(path):
    """
    Read the contents of a file.
    """
    with open(path) as f:
        return f.read()


setup(
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    name='eliot',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Logging as Storytelling",
    install_requires=["six", "zope.interface"],
    extras_require={
        "dev": [
            # Allows us to measure code coverage:
            "coverage",
        ]
    },
    keywords="logging",
    license="Apache 2.0",
    packages=["eliot", "eliot.tests"],
    url="https://github.com/ClusterHQ/eliot/",
    maintainer='Itamar Turner-Trauring',
    maintainer_email='itamar@clusterhq.com',
    long_description=read('README.rst'),
)
