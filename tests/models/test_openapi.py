import pytest
import re
import os
from laiagenlib.models.Openapi import OpenAPI

@pytest.fixture
def test_files(request):
    test_dir = os.path.dirname(os.path.abspath(request.module.__file__))
    input_file1 = os.path.join(test_dir, "..", "openapi_files", "api.yaml")
    input_file2 = os.path.join(test_dir, "..", "openapi_files", "api2.yaml")
    input_file3 = os.path.join(test_dir, "..", "openapi_files", "api3.yaml")
    yield input_file1, input_file2, input_file3

def test_create_models_file(test_files):
    input_file1, input_file2, input_file3 = test_files

    parser = OpenAPI(input_file1)
    assert len(parser.routes) == 8

    parser2 = OpenAPI(input_file2)
    assert len(parser2.routes) == 6

    parser3 = OpenAPI(input_file3)
    assert len(parser3.routes) == 1

    