import re

def update_file(filename: str, classes_info):
    with open(filename, "r") as file:
        file_content = file.read()

    for class_name, fields in classes_info.items():
        # Match class block header and body
        class_pattern = re.compile(
            rf"(^class\s+{class_name}\((?:LaiaBaseModel|LaiaUser)\):)(.+?)(?=^class\s|\Z)",
            re.DOTALL | re.MULTILINE
        )
        match = class_pattern.search(file_content)
        if not match:
            continue

        class_header = match.group(1)
        class_body = match.group(2)
        new_class_body = class_body

        for field in fields:
            if not field.extra:
                continue

            default_value = getattr(field, "default_value", "")
            
            # Match the field declaration in class_body
            if field.field_declaration:
                clean_decl = field.field_declaration.strip()
                if clean_decl.endswith(","):
                    clean_decl = clean_decl[:-1].strip()
                
                # Match Field(...) regardless of single/multi line
                pattern = re.compile(
                    rf"^(\s*){field.name}\s*:\s*{re.escape(field.type)}\s*=\s*Field\(\s*{re.escape(field.field_declaration)}\s*\)",
                    re.MULTILINE | re.DOTALL
                )
                replace_pattern = rf"\1{field.name}: {field.type} = Field({clean_decl}, {', '.join(field.extra)})"
            elif default_value:
                pattern = re.compile(
                    rf"^(\s*){field.name}\s*:\s*{re.escape(field.type)}\s*=\s*{re.escape(default_value)}",
                    re.MULTILINE | re.DOTALL
                )
                replace_pattern = rf"\1{field.name}: {field.type} = Field({default_value}, {', '.join(field.extra)})"
            else:
                pattern = re.compile(
                    rf"^(\s*){field.name}\s*:\s*{re.escape(field.type)}\s*$",
                    re.MULTILINE
                )
                replace_pattern = rf"\1{field.name}: {field.type} = Field(..., {', '.join(field.extra)})"

            new_class_body = pattern.sub(replace_pattern, new_class_body)

        old_class_block = match.group(0)
        new_class_block = class_header + new_class_body
        file_content = file_content.replace(old_class_block, new_class_block)

    with open(filename, "w") as file:
        file.write(file_content)