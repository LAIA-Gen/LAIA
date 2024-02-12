class OpenAPIRoute:
    def __init__(self, path, method, summary, responses, extensions):
        self.path = path
        self.method = method
        self.summary = summary
        self.responses = responses
        self.extensions = extensions

    def __str__(self):
        return f"Path: {self.path}, Method: {self.method}, Summary: {self.summary}, Responses: {self.responses}, Extensions: {self.extensions}"

class OpenAPIModel:
    def __init__(self, model_name, properties, required_properties):
        self.model_name = model_name
        self.properties = properties
        self.required_properties = required_properties

    def __str__(self):
        return f"Model: {self.model_name}, Properties: {self.properties}, Required Properties: {self.required_properties}"
