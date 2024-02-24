import pytest
import re
import os
from laiagenlib.utils.utils import create_models_file
from laiagenlib.utils.utils import validate_email, validate_password

@pytest.fixture
def test_files(request):
    test_dir = os.path.dirname(os.path.abspath(request.module.__file__))
    input_file1 = os.path.join(test_dir, "..", "openapi_files", "api.yaml")
    input_file2 = os.path.join(test_dir, "..", "openapi_files", "api2.yaml")
    input_file3 = os.path.join(test_dir, "..", "openapi_files", "api3.yaml")
    output_file = os.path.join(test_dir, "..", "openapi_files", "test_model.py")
    yield input_file1, input_file2, input_file3, output_file
    os.remove(output_file)

def test_create_models_file(test_files):
    input_file1, input_file2, input_file3, output_file = test_files

    # First OpenAPI file

    create_models_file(input_file1, output_file)
    assert os.path.exists(output_file)

    with open(output_file, 'r') as f:
        model_content = f.read()

    assert "from laiagenlib.models.Model import LaiaBaseModel" in model_content
    assert re.search(r'class\s+(\w+)\(LaiaBaseModel\):', model_content) is not None

    # Second OpenAPI file

    create_models_file(input_file2, output_file)
    assert os.path.exists(output_file)

    with open(output_file, 'r') as f:
        model_content = f.read()

    assert "from laiagenlib.models.Model import LaiaBaseModel" in model_content
    assert re.search(r'class\s+(\w+)\(LaiaBaseModel\):', model_content) is not None

    # Third OpenAPI file

    create_models_file(input_file3, output_file)
    assert os.path.exists(output_file)

    with open(output_file, 'r') as f:
        model_content = f.read()

    assert "from laiagenlib.models.Model import LaiaBaseModel" in model_content
    assert re.search(r'class\s+(\w+)\(LaiaBaseModel\):', model_content) is not None

def test_validate_email():
    # Valid email addresses
    assert validate_email("test@example.com") is True
    assert validate_email("user.name@example.co.uk") is True
    assert validate_email("user123@example.domain.com") is True

    # Invalid email addresses
    assert validate_email("invalid_email") is False
    assert validate_email("user@example") is False
    assert validate_email("user@.com") is False
    assert validate_email("@example.com") is False
    assert validate_email("user@example.") is False

def test_validate_password():
    assert validate_password("password123") is True
    assert validate_password("StrongPassword") is True

    assert validate_password("short") is False