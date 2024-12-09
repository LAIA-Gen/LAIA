from setuptools import find_packages, setup

setup(
    name='laia-gen-lib',
    packages=find_packages(),
    version='0.1.23',
    description='An AI application generator engine',
    author='Me',
    install_requires=['pymongo', 'pydantic==2.8.0', 'datamodel-code-generator==0.25.8', 'fastapi==0.111.0', 'bcrypt', 'asyncinit', 'pyjwt'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pymongo', 'pytest-asyncio', 'fastapi'],
    test_suite='tests',
)
