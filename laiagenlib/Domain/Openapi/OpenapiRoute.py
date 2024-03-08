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
