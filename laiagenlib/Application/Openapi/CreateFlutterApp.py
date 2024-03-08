import os
import subprocess
import yaml
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.Shared.Utils.ImportModel import import_model
from ...Domain.Openapi.FlutterBaseFiles import model_dart, home_dart

def create_flutter_app(openapi: OpenAPI=None, app_name:str="", app_path: str="", models_path: str=""):
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

    for openapiModel in openapi.models:
        model_module = import_model(models_path)
        model = getattr(model_module, openapiModel.model_name)
        model_file_content = model_dart(openapiModel, app_name, model)
        with open(os.path.join(app_path, 'lib', 'models', f'{model.__name__.lower()}.dart'), 'w') as f:
            f.write(model_file_content)


    home_file_content = home_dart(app_name, openapi.models)
    with open(os.path.join(app_path, 'lib', 'screens', 'home.dart'), 'w') as f:
        f.write(home_file_content)

