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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: System :: Logging',
    ],
    name='eliot',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Logging for Complex & Distributed Systems",
    install_requires=[
        # Python 3 compatibility:
        "six",
        # Internal code documentation:
        "zope.interface",
        # Persistent objects for Python:
        "pyrsistent >= 0.11.8",  # version with multi-type pvector/pmap_field
    ],
    extras_require={
        "journald": [
            # We use cffi to talk to the journald API:
            "cffi >= 1.1.2",  # significant API changes in older releases
        ],
        "dev": [
            # Allows us to measure code coverage:
            "coverage",
            # Bug-seeking missile:
            "hypothesis >= 1.14.0",
            # Tasteful testing for Python:
            "testtools",
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
    url="https://github.com/ClusterHQ/eliot/",
    maintainer='Itamar Turner-Trauring',
    maintainer_email='itamar@clusterhq.com',
    long_description=read('README.rst'),
)
