from typing import TypeVar
import subprocess
import re
from ..crud.crud import CRUD
from .logger import _logger

T = TypeVar('T', bound='BaseModel')

def create_models_file(input_file="openapi.yaml", output_file="model.py"):
    # This function uses the datamodel-code-generator for generating the pydantic models given a openapi.yaml file. 
    # The generated file is modified so that the pydantic models extend the LaiaBaseModel, this is necessary for 
    # using the Laia library

    subprocess.run(["datamodel-codegen", "--input", input_file, "--output", output_file], check=True)

    import_statement = """
# modified by laia-gen-lib:

from laiagenlib.models.Model import LaiaBaseModel"""

    with open(output_file, 'r') as f:
        model_content = f.read()

    lines = model_content.split('\n')
    import_index = next((i for i, line in enumerate(lines) if "from __future__ import annotations" in line), None)

    if import_index is not None:
        lines.insert(import_index + 1, import_statement)

    modified_content = '\n'.join(lines)
    modified_content = re.sub(r'class\s+(\w+)\(BaseModel\):', r'class \1(LaiaBaseModel):', modified_content)

    with open(output_file, 'w') as f:
        f.write(modified_content)

    print(f"File '{output_file}' created and modified.")

def create_flutter_app(app_name: str):
    # It creates the basic flutter project, with the required packages for using the arg-code-gen

    subprocess.run("flutter create " + app_name, shell=True)

    # TODO: change the following local dart libraries to the ones on the market

    project_path = "C:/Users/Usuario/OneDrive/Documents/TFG/test/flutter_app"

    # Add dependencies to the project
    subprocess.run(["flutter", "pub", "add", "C:/Users/Usuario/OneDrive/Documents/TFG/code_gen_arg/annotations", "-C", project_path], shell=True)
    subprocess.run(["flutter", "pub", "add", "--dev", "C:/Users/Usuario/OneDrive/Documents/TFG/code_gen_arg/riverpod_custom_generator", "-C", project_path], shell=True)
    subprocess.run(["flutter", "pub", "add", "--dev", "C:/Users/Usuario/OneDrive/Documents/TFG/code_gen_arg/widget_generator", "-C", project_path], shell=True)

async def create_element(element: T, crud_instance: CRUD):
    model_name = element.__class__.__name__.lower()

    return await crud_instance.post_item(model_name, element)
