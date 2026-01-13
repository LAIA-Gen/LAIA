import os
from typing import List
from .DownloadImage import download_image
from ....Domain.Openapi.FlutterBaseFiles import http_client, main_dart, api_dart, styles_dart, generic_dart, theme_dart, auth_scafold_dart, nav_bar_dart
from ....Domain.LaiaUser.Role import Role
from ....Domain.AccessRights.AccessRights import AccessRight
import shutil

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

    laia_models = [AccessRight, Role]
    for model in laia_models:
        image_url = "https://static.vecteezy.com/system/resources/thumbnails/024/983/914/small/simple-user-default-icon-free-png.png"
        image_name = model.__name__.lower() + ".png"
        image_path = os.path.join(assets_dir, image_name)
        download_image(image_url, image_path)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))

    local_image_path = os.path.join(current_dir, 'logo.png')
    local_image_path_home = os.path.join(current_dir, 'logo_home.png')

    shutil.copyfile(
        local_image_path,
        os.path.join(assets_dir, 'logo.png')
    )

    shutil.copyfile(
        local_image_path_home,
        os.path.join(assets_dir, 'logo_home.png')
    )

    directories = ['config', 'generic', 'models', 'screens', 'theme']
    for directory in directories:
        os.makedirs(os.path.join(dart_dir, directory), exist_ok=True)

    main_file_content = main_dart(app_name, models)
    with open(os.path.join(dart_dir, 'main.dart'), 'w') as f:
        f.write(main_file_content)

    api_file_content = api_dart()
    with open(os.path.join(dart_dir, 'config', 'api.dart'), 'w') as f:
        f.write(api_file_content)

    styles_file_content = styles_dart()
    with open(os.path.join(dart_dir, 'config', 'styles.dart'), 'w') as f:
        f.write(styles_file_content)

    http_file_content = http_client(app_name)
    with open(os.path.join(dart_dir, 'config', 'http_client.dart'), 'w') as f:
        f.write(http_file_content)
    
    generic_file_content = generic_dart(app_name)
    with open(os.path.join(dart_dir, 'generic', 'generic_widgets.dart'), 'w') as f:
        f.write(generic_file_content)

    nav_bar_file_content = nav_bar_dart(app_name)
    with open(os.path.join(dart_dir, 'generic', 'nav_bar.dart'), 'w') as f:
        f.write(nav_bar_file_content)

    theme_file_content = theme_dart()
    with open(os.path.join(dart_dir, 'theme', 'theme.dart'), 'w') as f:
        f.write(theme_file_content)

    auth_scaffold_file_content = auth_scafold_dart()
    with open(os.path.join(dart_dir, 'theme', 'auth_scaffold.dart'), 'w') as f:
        f.write(auth_scaffold_file_content)
