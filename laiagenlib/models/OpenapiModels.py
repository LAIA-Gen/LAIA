class OpenAPIRoute:
    def __init__(self, path, method, summary, responses, extensions, extra):
        self.path = path
        self.method = method
        self.summary = summary
        self.responses = responses
        self.extensions = extensions
        self.extra = extra

    def __str__(self):
        return f"Path: {self.path}, Method: {self.method}, Summary: {self.summary}, Responses: {self.responses}, Extensions: {self.extensions}, Extra Route: {self.extra}"

class OpenAPIModel:
    def __init__(self, model_name, properties, required_properties):
        self.model_name = model_name
        self.properties = properties
        self.required_properties = required_properties

    def __str__(self):
        return f"Model: {self.model_name}, Properties: {self.properties}, Required Properties: {self.required_properties}"

    def find_frontend_properties(self):
        frontend_properties = {}
        for prop_name, prop_details in self.properties.items():
            if any("x-frontend-" in key for key in prop_details):
                frontend_properties[prop_name] = {key.replace("x-frontend-", ""): value for key, value in prop_details.items() if key.startswith("x-frontend-")}
        return frontend_properties
    
    def find_extensions(self):
        extensions = {}
        for prop_name, prop_details in self.properties.items():
            if any("x-" in key for key in prop_details):
                extensions[prop_name] = {key: value for key, value in prop_details.items() if key.startswith("x-")}
        return extensions