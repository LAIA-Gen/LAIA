from setuptools import find_packages, setup

setup(
    name='laia-gen-lib',
    packages=find_packages(),
    version='0.1.3',
    description='An AI application generator engine',
    author='Me',
    install_requires=['pymongo', 'pydantic', 'datamodel-code-generator'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pymongo', 'pytest-asyncio'],
    test_suite='tests',
)