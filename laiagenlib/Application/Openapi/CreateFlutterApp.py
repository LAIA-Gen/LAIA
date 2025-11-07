import os
import subprocess
import textwrap
import yaml
import asyncio
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.LaiaUser.Role import Role
from ...Domain.Shared.Utils.ImportModel import import_model
from ...Domain.Openapi.FlutterBaseFiles import model_dart, home_dart, geojson_models_file
from ...Domain.Shared.Utils.logger import _logger

async def create_flutter_app(openapi: OpenAPI=None, app_name:str="", app_path: str="", models_path: str="", auth_required: bool = False, use_access_rights: bool = True):
    subprocess.run("flutter create " + app_name, shell=True)

    pubspec_content = textwrap.dedent(f"""
name: {app_name}
description: A new Flutter project.

publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.2.3 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  laia_annotations: ^0.0.7
  cupertino_icons: ^1.0.2
  json_annotation: ^4.8.1
  json_serializable: ^6.7.1
  flutter_riverpod: ^2.4.6
  http: ^1.1.0
  tuple: ^2.0.2
  copy_with_extension: ^4.0.0
  flutter_map: ^6.1.0
  flutter_map_arcgis: ^2.0.6
  dio: ^5.4.0
  latlong2: ^0.9.0
  flutter_typeahead: ^5.0.0
  dart_amqp: ^0.2.5
  geocoding: ^3.0.0
  shared_preferences: ^2.2.2

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.6
  laia_riverpod_custom_generator:
    path: /Volumes/DISK/Projects/Work/LAIA_Gen/laia_flutter_gen/laia_riverpod_custom_generator
  laia_widget_generator:
    path: /Volumes/DISK/Projects/Work/LAIA_Gen/laia_flutter_gen/laia_widget_generator
  riverpod_lint: ^2.0.1
  copy_with_extension_gen: ^4.0.0
  flutter_lints: ^2.0.0

flutter:
  assets:
    - assets/
  uses-material-design: true
""")
    
    with open(f"{app_name}/pubspec.yaml", "w", encoding="utf-8") as f:
        f.write(pubspec_content)    

    await run(f"flutter pub get -C ./{app_name}")
    
    models_dir = os.path.join(f"./{app_name}", "lib", "models")
    screens_dir = os.path.join(f"./{app_name}", "lib", "screens")   
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(screens_dir, exist_ok=True)

    for openapiModel in openapi.models:
        if openapiModel.model_name.startswith("Body_"):
            continue
        model_module = import_model(models_path)
        model = getattr(model_module, openapiModel.model_name)
        model_file_content = model_dart(openapiModel, app_name, model)
        with open(os.path.join(models_dir, f'{model.__name__.lower()}.dart'), 'w') as f:
            f.write(model_file_content)
    
    with open(os.path.join(models_dir, 'geometry.dart'), 'w') as f:
        f.write(geojson_models_file())

    if auth_required:
        laia_models = {'AccessRight': AccessRight, 'Role': Role}
        for laiaModel in openapi.laia_models:
            model = laia_models.get(laiaModel.model_name)
            model_file_content = model_dart(openapiModel=laiaModel, app_name=app_name, model=model)
            with open(os.path.join(models_dir, f'{model.__name__.lower()}.dart'), 'w') as f:
                f.write(model_file_content)

    home_file_content = home_dart(app_name, openapi.models, use_access_rights)
    with open(os.path.join(screens_dir, 'home.dart'), 'w') as f:
        f.write(home_file_content)

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')