from typing import List

class OpenAPIModel:
    model_name: str
    properties: dict
    required_properties: List[str]
    extensions: dict

    def __init__(self, model_name, properties, required_properties, extensions = {}):
        self.model_name = model_name
        self.properties = properties
        self.required_properties = required_properties
        self.extensions = extensions

    def __str__(self):
        return f"Model: {self.model_name}, Properties: {self.properties}, Required Properties: {self.required_properties}, Extensions: {self.extensions}"

    def get_frontend_properties(self):
        frontend_properties = {}
        for prop_name, prop_details in self.properties.items():
            if any("x_frontend_" in key for key in prop_details):
                frontend_properties[prop_name] = {key.replace("x_frontend_", ""): value for key, value in prop_details.items() if key.startswith("x_frontend_")}
        return frontend_properties
    
    def get_field_extensions(self):
        extensions = {}
        for prop_name, prop_details in self.properties.items():
            if any("x_" in key for key in prop_details):
                extensions[prop_name] = {key: value for key, value in prop_details.items() if key.startswith("x_")}
        return extensions