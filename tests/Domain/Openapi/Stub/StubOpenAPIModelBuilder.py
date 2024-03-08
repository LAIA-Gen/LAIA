import random
from typing import List
from laiagenlib.Domain.Openapi.OpenapiModel import OpenAPIModel

class StubOpenAPIModelBuilder:
    model_name: str
    properties: dict
    required_properties: List[str]

    def __init__(self, model_name):
        self.model_name = model_name
        self.properties = {}
        self.required_properties = ["id", "name"]

        self.generate_random_properties()

    def generate_random_properties(self):
        for prop_name in ["prop1", "prop2", "prop3"]:
            self.with_property(prop_name, {"type": random.choice(["string", "number", "boolean"])})

    def with_property(self, prop_name, prop_details):
        self.properties[prop_name] = prop_details
        return self

    def build(self):
        return OpenAPIModel(self.model_name, self.properties, self.required_properties)
