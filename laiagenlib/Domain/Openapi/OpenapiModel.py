class OpenAPIModel:
    model_name: str
    properties: dict
    required_properties: dict
    extensions: dict

    def __init__(self, model_name, properties, required_properties, extensions):
        self.model_name = model_name
        self.properties = properties
        self.required_properties = required_properties
        self.extensions = extensions

    def __str__(self):
        return f"Model: {self.model_name}, Properties: {self.properties}, Required Properties: {self.required_properties}, Extensions: {self.extensions}"
