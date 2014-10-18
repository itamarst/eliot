import os

from setuptools import setup


def get_version():
    """
    Get the version from version module without importing more than
    necessary.
    """
    version_module_path = os.path.join(os.path.dirname(__file__), "eliot",
                                       "_version.py")

    # The version module contains a variable called __version__
    with open(version_module_path) as version_module:
        exec(version_module.read())
    return locals()["__version__"]


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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    name='eliot',
    version=get_version(),
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
