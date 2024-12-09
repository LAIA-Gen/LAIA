from setuptools import find_packages, setup

setup(
    name='laia-gen-lib',
    packages=find_packages(),
    version='0.1.22',
    description='An AI application generator engine',
    author='Me',
    install_requires=['pymongo', 'pydantic', 'datamodel-code-generator==0.25.8', 'fastapi', 'bcrypt', 'asyncinit', 'pyjwt'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pymongo', 'pytest-asyncio', 'fastapi'],
    test_suite='tests',
)
