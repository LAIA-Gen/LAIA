from importlib.util import spec_from_file_location, module_from_spec

def import_model(models_path):
    spec = spec_from_file_location("models", models_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module