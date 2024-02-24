from typing import TypeVar, List
import subprocess
import requests
import re
import os
import yaml
import time
from ..crud.crud import CRUD
from .flutter_base_files import main_dart, api_dart, styles_dart, generic_dart
from .logger import _logger

T = TypeVar('T', bound='BaseModel')

def create_models_file(input_file="openapi.yaml", output_file="model.py", models: List[any] = []):
    # This function uses the datamodel-code-generator for generating the pydantic models given a openapi.yaml file. 
    # The generated file is modified so that the pydantic models extend the LaiaBaseModel, this is necessary for 
    # using the Laia library

    subprocess.run(["datamodel-codegen", "--input", input_file, "--output", output_file], check=True)

    import_statement = """
# modified by laia-gen-lib:

from laiagenlib.models.Model import LaiaBaseModel
from laiagenlib.models.User import LaiaUser"""

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

    with open(output_file, 'r') as f:
        model_content = f.read()

    classes_info = extract_class_info(model_content, models)
    update_file(output_file, classes_info)

    _logger.info(f"File '{output_file}' created and modified.")

class FieldInfo:
    def __init__(self, name, type, field_declaration, extra):
        self.name = name
        self.type = type
        self.field_declaration = field_declaration
        self.extra = extra

def extract_class_info(file_content, models):
    class_info = {}
    class_pattern = re.compile(r"class\s+(\w+)\((\w+)\):(?:.*?)(?=class|\Z)", re.DOTALL)
    field_pattern = re.compile(r"^\s{4}(\w+):\s*(.+?)\s*=\s*Field\((.*?)\)", re.DOTALL | re.MULTILINE)

    classes = class_pattern.findall(file_content)
    for class_name, base_class in classes:
        fields = []
        class_content = re.search(r"class\s+" + class_name + r"\(.*?\):(.+?)(?=class|\Z)", file_content, re.DOTALL)
        if class_content:
            field_matches = field_pattern.findall(class_content.group(1))
            model = next((model for model in models if model.model_name == class_name), None)
            if model:
                extensions = model.find_extensions()
                for field_name, type, field_declaration in field_matches:
                    extra_data_dict = extensions.get(field_name, {})
                    extra_data_list = [f"{key.replace('-', '_')}='{value}'" if isinstance(value, str) else f"{key.replace('-', '_')}={value}" for key, value in extra_data_dict.items()]
                    fields.append(FieldInfo(field_name, type, field_declaration, extra=extra_data_list))
                class_info[class_name] = fields
    return class_info

def update_file(filename, classes_info):
    with open(filename, "r") as file:
        file_content = file.readlines()

    for class_name, fields in classes_info.items():
        class_pattern = re.compile(r"class\s+" + class_name + r"\(LaiaBaseModel\):")
        in_class = False

        for i, line in enumerate(file_content):
            if re.match(class_pattern, line):
                in_class = True
            elif in_class and line.strip() == "":
                in_class = False

            if in_class:
                for field in fields:
                    field_declaration = f"{field.name}: {field.type} = Field({field.field_declaration})"
                    replace_pattern = f"{field.name}: {field.type} = Field({field.field_declaration}, {', '.join(field.extra)})"

                    if re.search(re.escape(field_declaration), line):
                        file_content[i] = re.sub(re.escape(field_declaration), replace_pattern, line)

    with open(filename, "w") as file:
        file.writelines(file_content)

def create_routes_file(path: str):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write("""from fastapi import APIRouter

router = APIRouter(tags=["Extra Routes"])

__all__ = ['router']""")
        _logger.info(f"Routes file created at {path}")
    else:
        _logger.info(f"Routes file already exists at {path}")

def create_flutter_app(app_name: str):
    # It creates the basic flutter project, with the required packages for using the arg-code-gen

    subprocess.run("flutter create " + app_name, shell=True)

    # TODO: change the following local dart libraries to the ones on the market
    subprocess.run("flutter pub add annotations --path=C:/Users/Usuario/OneDrive/Documents/TFG/code_gen_arg/annotations -C " + f"./{app_name}", shell=True)
    subprocess.run("flutter pub add --dev riverpod_custom_generator --path=C:/Users/Usuario/OneDrive/Documents/TFG/code_gen_arg/riverpod_custom_generator -C " + f"./{app_name}", shell=True)
    subprocess.run("flutter pub add --dev widget_generator --path=C:/Users/Usuario/OneDrive/Documents/TFG/code_gen_arg/widget_generator -C " + f"./{app_name}", shell=True)
    subprocess.run("flutter pub add json_annotation:^4.8.1 json_serializable:^6.7.1 flutter_riverpod:^2.4.6 http:^1.1.0 tuple:^2.0.2 copy_with_extension:^4.0.0 flutter_map:^6.1.0 flutter_map_arcgis:^2.0.6 dio:^5.4.0 latlong2:^0.9.0 flutter_typeahead:^5.0.0 dart_amqp:^0.2.5 -C " + f"./{app_name}", shell=True)
    subprocess.run("flutter pub add --dev riverpod_lint:^2.0.1 build_runner:^2.4.6 copy_with_extension_gen:^4.0.4 -C " + f"./{app_name}", shell=True)

    assets = "assets/"
    with open(f"{app_name}/pubspec.yaml", "r") as file:
        pubspec_content = yaml.safe_load(file)
    if 'flutter' not in pubspec_content:
        pubspec_content['flutter'] = {}
    if 'assets' not in pubspec_content['flutter']:
        pubspec_content['flutter']['assets'] = []
    pubspec_content['flutter']['assets'].append(assets)
    with open(f"{app_name}/pubspec.yaml", "w") as file:
        yaml.dump(pubspec_content, file)

def download_image(url: str, destination: str):
    response = requests.get(url)
    if response.status_code == 200:
        with open(destination, 'wb') as f:
            f.write(response.content)

def create_base_files(app_name: str, models: List[any] = []):
    dart_dir = os.path.join(app_name, 'lib')
    os.makedirs(dart_dir, exist_ok=True)

    assets_dir = os.path.join(app_name, 'assets')
    os.makedirs(assets_dir, exist_ok=True)

    for model in models:
        image_url = "https://static.vecteezy.com/system/resources/thumbnails/024/983/914/small/simple-user-default-icon-free-png.png"
        image_name = model.model_name.lower() + ".png"
        image_path = os.path.join(assets_dir, image_name)
        download_image(image_url, image_path)

    directories = ['config', 'generic', 'models', 'screens']
    for directory in directories:
        os.makedirs(os.path.join(dart_dir, directory), exist_ok=True)

    main_file_content = main_dart(app_name)
    with open(os.path.join(dart_dir, 'main.dart'), 'w') as f:
        f.write(main_file_content)

    api_file_content = api_dart()
    with open(os.path.join(dart_dir, 'config', 'api.dart'), 'w') as f:
        f.write(api_file_content)

    styles_file_content = styles_dart()
    with open(os.path.join(dart_dir, 'config', 'styles.dart'), 'w') as f:
        f.write(styles_file_content)
    
    generic_file_content = generic_dart(app_name)
    with open(os.path.join(dart_dir, 'generic', 'generic_widgets.dart'), 'w') as f:
        f.write(generic_file_content)

def call_arg_code_gen(app_name: str):
    subprocess.run("flutter clean", cwd=f"./{app_name}", shell=True)
    time.sleep(5)
    subprocess.run(["flutter", "pub", "run", "build_runner", "build"], cwd=f"./{app_name}", shell=True)
    time.sleep(5)
    subprocess.Popen("flutter run -d chrome", cwd=f"./{app_name}", shell=True)
    
async def create_element(element: T, crud_instance: CRUD):
    model_name = element.__class__.__name__.lower()

    return await crud_instance.post_item(model_name, element.dict())

def validate_email(email: str) -> bool:
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

def validate_password(password: str) -> bool:
    return len(password) >= 8
