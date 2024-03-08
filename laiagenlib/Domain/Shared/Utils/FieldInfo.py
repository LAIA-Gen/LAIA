class FieldInfo:
    name: str = ""
    type: str = ""
    field_declaration: str = ""
    extra: str = ""

    def __init__(self, name, type, field_declaration, extra):
        self.name = name
        self.type = type
        self.field_declaration = field_declaration
        self.extra = extra
