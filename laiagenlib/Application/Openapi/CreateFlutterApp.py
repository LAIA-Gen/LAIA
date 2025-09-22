import os
import subprocess
import yaml
import asyncio
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.LaiaUser.Role import Role
from ...Domain.Shared.Utils.ImportModel import import_model
from ...Domain.Openapi.FlutterBaseFiles import model_dart, home_dart, geojson_models_file

async def create_flutter_app(openapi: OpenAPI=None, app_name:str="", app_path: str="", models_path: str="", auth_required: bool = False):
    subprocess.run("flutter create " + app_name, shell=True)

    # TODO: change the following local dart libraries to the ones on the marketç
    await run(f"flutter pub add laia_annotations -C ./{app_name}")
    await run(f"flutter pub add --dev laia_riverpod_custom_generator -C ./{app_name}")
    await run(f"flutter pub add --dev laia_widget_generator -C ./{app_name}")
    await run(f"flutter pub add collection json_annotation json_serializable flutter_riverpod http tuple copy_with_extension flutter_map flutter_map_arcgis dio latlong2 flutter_typeahead dart_amqp shared_preferences -C ./{app_name}")
    await run(f"flutter pub add --dev riverpod_lint build_runner copy_with_extension_gen flutter_lints -C ./{app_name}")
    
    models_dir = os.path.join(f"./{app_name}", "lib", "models")
    screens_dir = os.path.join(f"./{app_name}", "lib", "screens")   
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(screens_dir, exist_ok=True)

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

    home_file_content = home_dart(app_name, openapi.models)
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