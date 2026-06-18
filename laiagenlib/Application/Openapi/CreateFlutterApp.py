import os
import subprocess
import yaml
import asyncio
from enum import EnumMeta
from pydantic import BaseModel

from ...Domain.Email.EmailRequest import EmailRequest

from ...Domain.Shard.Shard import Shard
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.LaiaUser.Role import Role
from ...Domain.Shared.Utils.ImportModel import import_model
from ...Domain.Openapi.FlutterBaseFiles import model_dart, home_dart, geojson_models_file, embedded_model_dart, embedded_class_name_from_annotation

LAIA_INTERNAL_MODELS = {
    "Shard": Shard,
    "EmailRequest": EmailRequest,
    # "AccessRight": AccessRight,  (si quieres unificar aquí también)
    # "Role": Role,
}

async def create_flutter_app(openapi: OpenAPI=None, app_name:str="", app_path: str="", models_path: str="", auth_required: bool = False, use_access_rights: bool = True):
    print("CREATING FLUTTER APP")

    subprocess.run("flutter create " + app_name, shell=True)

    # Environment Configurations
    project_config_dir = os.path.join(app_name, 'lib/config')

    #if not os.path.exists(os.path.join(project_config_dir, '.env.development')):
    #    with open(os.path.join(project_config_dir, '.env.development'), 'w') as f:
    #        f.write('API_URL=http://localhost:8000')
        
    if not os.path.exists(os.path.join(project_config_dir, '.env.production')):
        with open(os.path.join(project_config_dir, '.env.production'), 'w') as f:
            f.write('API_URL=http://localhost:8009')

    # TODO: change the following local dart libraries to the ones on the marketç
    await run(f"flutter pub add laia_annotations -C ./{app_name}")
    #await run(f"flutter pub add --dev laia_riverpod_custom_generator -C ./{app_name}")
    #await run(f"flutter pub add --dev laia_widget_generator -C ./{app_name}")
    await run(f"flutter pub add collection:^1.18.0 json_annotation:^4.8.1 json_serializable:^6.7.1 flutter_riverpod:^2.4.6 http:^1.1.0 tuple:^2.0.2 copy_with_extension:^4.0.0 flutter_map:^6.1.0 flutter_map_arcgis:^2.0.6 dio:^5.4.0 latlong2:^0.9.0 flutter_typeahead:^5.0.0 dart_amqp:^0.2.5 geocoding:^3.0.0 shared_preferences:^2.2.2 package_info_plus:^8.0.0 flutter_quill:^11.4.0 -C ./{app_name}")
    await run(f"flutter pub add --dev riverpod_lint:^2.0.1 build_runner:^2.4.6 copy_with_extension_gen:^4.0.0 flutter_lints:^2.0.0 -C ./{app_name}")

    pubspec_path = f"{app_name}/pubspec.yaml"

    with open(pubspec_path, "r") as f:
        pubspec = yaml.safe_load(f)

    pubspec.setdefault("dev_dependencies", {})

    # pubspec["dev_dependencies"]["laia_riverpod_custom_generator"] = {
    #     "path": "C:/Users/joelm/OneDrive/Escritorio/LaiaBackend/laia_flutter_gen/laia_riverpod_custom_generator"
    # }

    # pubspec["dev_dependencies"]["laia_widget_generator"] = {
    #     "path": "C:/Users/joelm/OneDrive/Escritorio/LaiaBackend/laia_flutter_gen/laia_widget_generator"
    # }

    pubspec["dev_dependencies"]["laia_riverpod_custom_generator"] = {
        "path": "/laia_flutter_gen/laia_riverpod_custom_generator"
    }

    pubspec["dev_dependencies"]["laia_widget_generator"] = {
        "path": "/laia_flutter_gen/laia_widget_generator"
    }

    #pubspec.setdefault("dependencies", {})
    #pubspec["dependencies"]["laia_annotations"] = {
    #    "path": "/laia_flutter_gen/laia_annotations"
    #}
    pubspec["dependencies"]["flutter_localizations"] = {
        "sdk": "flutter"
    }

    #await run(f"flutter pub get ./{app_name}")

    with open(pubspec_path, "w") as f:
        yaml.dump(pubspec, f, sort_keys=False)
    
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

    model_module = import_model(models_path)
    openapi_model_names = {model.model_name.replace('-Input', '').replace('-Output', '') for model in openapi.models}
    embedded_model_names = set()

    for openapiModel in openapi.models:
        model_name_clean = openapiModel.model_name.replace('-Input', '').replace('-Output', '')
        if not hasattr(model_module, model_name_clean):
            continue
        model = getattr(model_module, model_name_clean)
        for prop_name, annotation in getattr(model, "__annotations__", {}).items():
            prop_details = openapiModel.properties.get(prop_name, {})
            if isinstance(prop_details, dict) and prop_details.get("x_frontend_relation"):
                continue
            embedded_cls_name = embedded_class_name_from_annotation(annotation)
            if not embedded_cls_name or embedded_cls_name not in openapi_model_names:
                continue
            embedded_cls = getattr(model_module, embedded_cls_name, None)
            if (
                embedded_cls is not None
                and isinstance(embedded_cls, type)
                and issubclass(embedded_cls, BaseModel)
                and not isinstance(embedded_cls, EnumMeta)
            ):
                embedded_model_names.add(embedded_cls_name)

    frontend_models = [
        model for model in openapi.models
        if model.model_name.replace('-Input', '').replace('-Output', '') not in embedded_model_names
    ]

    home_txt_path = os.path.join(f"./{app_name}", "lib", "home.txt")
    with open(home_txt_path, 'w') as f:
        seen_home = set()
        for m in frontend_models:
            if m.model_name.startswith("Body_") or m.model_name.endswith("Update"):
                continue
            model_name_clean = m.model_name.replace('-Input', '').replace('-Output', '')
            if model_name_clean in seen_home:
                continue
            seen_home.add(model_name_clean)
            cls = getattr(model_module, model_name_clean, None)
            if cls is None and model_name_clean in LAIA_INTERNAL_MODELS:
                cls = LAIA_INTERNAL_MODELS[model_name_clean]
            if cls is None or isinstance(cls, EnumMeta):
                continue
            f.write(f"{model_name_clean}HomeWidget\n")

    generated_models = set()
    for openapiModel in frontend_models:
        if openapiModel.model_name.startswith("Body_"):
            continue

        if openapiModel.model_name.endswith("Update"):
            print(f"Skipping model: {openapiModel.model_name}")
            continue

        model_name_clean = openapiModel.model_name.replace('-Input', '').replace('-Output', '')
        if model_name_clean in generated_models:
            print(f"Skipping already generated model: {model_name_clean}")
            continue
        generated_models.add(model_name_clean)

        print(f"Generating model: {model_name_clean}")

        if hasattr(model_module, model_name_clean):
            model = getattr(model_module, model_name_clean)

        elif model_name_clean in LAIA_INTERNAL_MODELS:
            model = LAIA_INTERNAL_MODELS[model_name_clean]

        else:
            continue  # Skip models that are not found

        model_file_content = model_dart(openapiModel, app_name, model)
        with open(os.path.join(models_dir, f'{model_name_clean.lower()}.dart'), 'w') as f:
            f.write(model_file_content)

        for prop_name, ann in getattr(model, "__annotations__", {}).items():
            prop_details = openapiModel.properties.get(prop_name, {})
            has_embedded_extension = isinstance(prop_details, dict) and (
                prop_details.get('x_embedded') or prop_details.get('x-embedded')
            )
            embedded_cls_name = embedded_class_name_from_annotation(ann)
            if not embedded_cls_name or (
                not has_embedded_extension and embedded_cls_name not in embedded_model_names
            ):
                continue
            if hasattr(model_module, embedded_cls_name):
                embedded_cls = getattr(model_module, embedded_cls_name)
                embedded_content = embedded_model_dart(embedded_cls_name, app_name, embedded_cls)
                with open(os.path.join(models_dir, f'{embedded_cls_name.lower()}.dart'), 'w') as f:
                    f.write(embedded_content)

    with open(os.path.join(models_dir, 'geometry.dart'), 'w') as f:
        f.write(geojson_models_file())

    if auth_required:
        laia_models = {'AccessRight': AccessRight, 'Role': Role}
        for laiaModel in openapi.laia_models:
            model = laia_models.get(laiaModel.model_name)
            model_file_content = model_dart(openapiModel=laiaModel, app_name=app_name, model=model)
            with open(os.path.join(models_dir, f'{model.__name__.lower()}.dart'), 'w') as f:
                f.write(model_file_content)

    home_file_content = home_dart(app_name, frontend_models, use_access_rights)
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
