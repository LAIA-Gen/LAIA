import re

def update_file(filename: str, classes_info):
    with open(filename, "r") as file:
        file_content = file.readlines()

    for class_name, fields in classes_info.items():
        class_pattern = re.compile(r"class\s+" + class_name + r"\((LaiaBaseModel|LaiaUser)\):")
        in_class = False

        for i, line in enumerate(file_content):
            if re.match(class_pattern, line):
                in_class = True
            elif in_class and line.strip() == "":
                in_class = False

            if in_class:
                for field in fields:
                    field_declaration = f"{field.name}: {field.type} = Field({field.field_declaration})"
                    replace_pattern = f"{field.name}: {field.type} = Field({field.field_declaration}, {', '.join(field.extra)})"

                    if re.search(re.escape(field_declaration), line):
                        file_content[i] = re.sub(re.escape(field_declaration), replace_pattern, line)

    with open(filename, "w") as file:
        file.writelines(file_content)