import re
from ....Domain.Shared.Utils.FieldInfo import FieldInfo

def extract_class_info(file_content, models):
    class_info = {}
    class_pattern = re.compile(r"class\s+(\w+)\((\w+)\):(?:.*?)(?=class|\Z)", re.DOTALL)
    field_pattern = re.compile(r"^\s{4}(\w+):\s*(.+?)\s*=\s*Field\((.*?)\)", re.DOTALL | re.MULTILINE)

    classes = class_pattern.findall(file_content)
    for class_name, base_class in classes:
        fields = []
        class_content = re.search(r"class\s+" + class_name + r"\(.*?\):(.+?)(?=class|\Z)", file_content, re.DOTALL)
        if class_content:
            field_matches = field_pattern.findall(class_content.group(1))
            model = next((model for model in models if model.model_name == class_name), None)
            if model:
                extensions = model.get_field_extensions()
                for field_name, type, field_declaration in field_matches:
                    extra_data_dict = extensions.get(field_name, {})
                    extra_data_list = [f'{key.replace("-", "_")}="{value}"' if isinstance(value, str) else f"{key.replace('-', '_')}={value}" for key, value in extra_data_dict.items()]
                    fields.append(FieldInfo(field_name, type, field_declaration, extra=extra_data_list))
                class_info[class_name] = fields
    return class_info