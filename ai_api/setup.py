from setuptools import find_packages, setup

setup(
    name='argapilib',
    packages=find_packages(include=['argapilib']),
    version='0.1.1',
    description='My first Python library',
    author='Me',
    install_requires=['pymongo', 'pydantic'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pymongo', 'pytest-asyncio'],
    test_suite='tests',
)