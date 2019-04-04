from setuptools import setup

import versioneer


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
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: System :: Logging',
    ],
    name='eliot',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Logging library that tells you why it happened",
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, != 3.4.*',
    install_requires=[
        # Python 3 compatibility:
        "six",
        # Internal code documentation:
        "zope.interface",
        # Persistent objects for Python:
        "pyrsistent >= 0.11.8",  # version with multi-type pvector/pmap_field
        # Better decorators, with version that works better with type annotations:
        "boltons >= 19.0.1"
    ],
    extras_require={
        "journald": [
            # We use cffi to talk to the journald API:
            "cffi >= 1.1.2",  # significant API changes in older releases
        ],
        "dev": [
            # Ensure we can do python_requires correctly:
            "setuptools >= 40",
            # For uploading releases:
            "twine >= 1.12.1",
            # Allows us to measure code coverage:
            "coverage",
            # Bug-seeking missile:
            "hypothesis >= 1.14.0",
            # Tasteful testing for Python:
            "testtools",
            "sphinx",
            "sphinx_rtd_theme",
            "flake8",
            "yapf",
            "pytest"
        ]
    },
    entry_points={
        'console_scripts': [
            'eliot-prettyprint = eliot.prettyprint:_main',
        ]
    },
    keywords="logging",
    license="Apache 2.0",
    packages=["eliot", "eliot.tests"],
    url="https://github.com/itamarst/eliot/",
    maintainer='Itamar Turner-Trauring',
    maintainer_email='itamar@itamarst.org',
    long_description=read('README.rst'),
)
