from typing import TypeVar, List
from pydantic import BaseModel
import subprocess
import re
from .ExtractClassInfo import extract_class_info
from .UpdateFile import update_file
from ....Domain.Shared.Utils.logger import _logger

import re
from typing import List

FIELD_START_RE = re.compile(r'^\s*[A-Za-z_]\w*\s*:\s*.*=\s*Field\(\s*$')

def _make_update_class_block(class_body: str) -> str:
    """
    Genera un body para Update:
    - Mantiene decoradores y defs y model_config.
    - Convierte campos a Optional[...] = None.
    - IMPORTANTE: ignora completamente los bloques multilínea de Field(...),
      porque en Update no queremos arrastrar esas líneas.
    """
    out_lines = []
    skipping_field_block = False
    field_paren_balance = 0

    for line in class_body.splitlines():
        # Si estamos saltando un bloque Field(...), seguimos hasta cerrar paréntesis
        if skipping_field_block:
            field_paren_balance += line.count("(") - line.count(")")
            if field_paren_balance <= 0:
                skipping_field_block = False
            continue

        # Mantener decoradores / defs (validators, etc.)
        if re.match(r'^\s*@', line) or re.match(r'^\s*def\s+', line):
            out_lines.append(line)
            continue

        # Mantener model_config
        if re.match(r'^\s*model_config\s*=', line):
            out_lines.append(line)
            continue

        # Si es un campo que empieza con "= Field(" en la misma línea y abre paréntesis multilínea:
        # ejemplo: district: Optional[str] = Field(
        if FIELD_START_RE.match(line):
            # Convertimos ese campo a Optional[...] = None y saltamos el bloque Field completo
            m = re.match(r'^(\s*)([A-Za-z_]\w*)\s*:\s*([^=\n]+?)\s*=\s*Field\(\s*$', line)
            if m:
                indent, field, typ = m.groups()
                typ = typ.strip()
                new_type = typ if "Optional[" in typ or ("Union[" in typ and "None" in typ) or ("|" in typ and "None" in typ) else f"Optional[{typ}]"
                out_lines.append(f"{indent}{field}: {new_type} = None")

                skipping_field_block = True
                field_paren_balance = 1  # ya vimos un "(" en Field(
            continue

        # Campo en una sola línea con Field(...):
        # title: str = Field(..., description="...")
        m_field_inline = re.match(r'^(\s*)([A-Za-z_]\w*)\s*:\s*([^=\n]+?)\s*=\s*Field\(.*\)\s*$', line)
        if m_field_inline:
            indent, field, typ = m_field_inline.groups()
            typ = typ.strip()
            new_type = typ if "Optional[" in typ or ("Union[" in typ and "None" in typ) or ("|" in typ and "None" in typ) else f"Optional[{typ}]"
            out_lines.append(f"{indent}{field}: {new_type} = None")
            continue

        # Campo normal (sin Field)
        m = re.match(r'^(\s*)([A-Za-z_]\w*)\s*:\s*([^=\n]+?)(\s*=\s*.+)?\s*$', line)
        if m:
            indent, field, typ, _default = m.groups()
            if field == "model_config":
                out_lines.append(line)
                continue

            typ = typ.strip()
            new_type = typ if "Optional[" in typ or ("Union[" in typ and "None" in typ) or ("|" in typ and "None" in typ) else f"Optional[{typ}]"
            out_lines.append(f"{indent}{field}: {new_type} = None")
            continue

        # Otras líneas (docstrings, comentarios, pass, etc.)
        if line.strip():
            out_lines.append(line)

    return "\n".join(out_lines).rstrip()


def add_update_models_at_end(modified_content: str, models: List[any]) -> str:
    """
    Genera clases {Model}Update y las añade al FINAL del archivo.
    """
    updates_blocks = []

    for model in models:
        name = model.model_name
        update_name = f"{name}Update"

        # Si ya existe, skip
        if re.search(rf'^\s*class\s+{re.escape(update_name)}\(', modified_content, re.MULTILINE):
            continue

        # Captura clase original (header+body) sin depender de inserciones
        pattern = re.compile(
            rf'(^class\s+{re.escape(name)}\([^\)]*\):\n)(.*?)(?=^\s*class\s|\Z)',
            re.DOTALL | re.MULTILINE
        )
        m = pattern.search(modified_content)
        if not m:
            continue

        class_header, class_body = m.group(1), m.group(2)

        # Padre real
        parent_m = re.match(rf'class\s+{re.escape(name)}\(([^)]+)\):', class_header.strip())
        parent = parent_m.group(1).strip() if parent_m else "LaiaBaseModel"

        update_body = _make_update_class_block(class_body)

        updates_blocks.append(f"\n\nclass {update_name}({parent}):\n{update_body}\n")

    if not updates_blocks:
        return modified_content

    # Asegura Optional import (sin duplicar en la misma línea)
    # Tu import_statement tiene "from typing import Annotated" justo después del future import.
    # Añadimos Optional SOLO si no existe ya un "from typing import ... Optional".
    if not re.search(r'^from typing import .*Optional', modified_content, re.MULTILINE):
        modified_content = modified_content.replace(
            "from typing import Annotated",
            "from typing import Annotated, Optional",
            1
        )

    return modified_content.rstrip() + "\n\n# ---- Auto-generated Update models ----\n" + "".join(updates_blocks)

T = TypeVar('T', bound='BaseModel')

def _extract_embedded_class_name(field_type: str):
    primitives = {'str', 'int', 'float', 'bool', 'Any', 'Dict', 'datetime', 'date'}
    field_type = field_type.strip().strip("'\"")
    cls_match = (
        re.match(r'Optional\[(?:List|list)\[(\w+)\]\]', field_type) or
        re.match(r'(?:List|list)\[(\w+)\]', field_type) or
        re.match(r'Optional\[(\w+)\]', field_type) or
        re.match(r'^(\w+)$', field_type)
    )
    if not cls_match:
        return None

    cls_name = cls_match.group(1)
    return None if cls_name in primitives else cls_name


def _get_class_body(modified_content: str, class_name: str):
    pattern = re.compile(
        rf'(^class\s+{re.escape(class_name)}\([^\)]*\):\n)(.*?)(?=^\s*class\s|\Z)',
        re.DOTALL | re.MULTILINE
    )
    match = pattern.search(modified_content)
    return match.group(2) if match else ""


def _get_embedded_class_names(modified_content: str, models: List[any]) -> set:
    embedded_classes = set()
    for model in models:
        if not hasattr(model, 'properties'):
            continue
        class_body = _get_class_body(modified_content, model.model_name)
        for prop_name, prop in model.properties.items():
            if not isinstance(prop, dict) or not (prop.get('x_embedded') or prop.get('x-embedded')):
                continue
            m = re.search(
                rf'^\s+{re.escape(prop_name)}\s*:\s*(.+?)(?:\s*=.*)?$',
                class_body,
                re.MULTILINE
            )
            if not m:
                continue
            cls_name = _extract_embedded_class_name(m.group(1))
            if cls_name:
                embedded_classes.add(cls_name)
    return embedded_classes

def create_models_file(input_file="openapi.yaml", output_file="model.py", models: List[any] = [], excluded_models: List[str] = []):
    # This function uses the datamodel-code-generator for generating the pydantic models given a openapi.yaml file. 
    # The generated file is modified so that the pydantic models extend the LaiaBaseModel, this is necessary for 
    # using the Laia library

    subprocess.run(["datamodel-codegen", "--input", input_file, "--output", output_file], check=True)

    import_statement = """
# modified by laia-gen-lib:

from typing import Annotated
from pydantic import ConfigDict, field_validator
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from laiagenlib.Domain.LaiaUser.LaiaUser import LaiaUser
from laiagenlib.Domain.GeoJSON.Geometry import Type, Geometry, LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon
from laiagenlib.Domain.Shared.Types.objectid_annotation import ObjectIdPydanticAnnotation
from bson import ObjectId"""

    with open(output_file, 'r') as f:
        model_content = f.read()

    lines = model_content.split('\n')
    import_index = next((i for i, line in enumerate(lines) if "from __future__ import annotations" in line), None)

    if import_index is not None:
        lines.insert(import_index + 1, import_statement)

    modified_content = '\n'.join(lines)
    modified_content = re.sub(r'class\s+(\w+)\(BaseModel\):', r'class \1(LaiaBaseModel):', modified_content)

    embedded_classes = _get_embedded_class_names(modified_content, models)
    for cls_name in embedded_classes:
        modified_content = modified_content.replace(
            f'class {cls_name}(LaiaBaseModel):',
            f'class {cls_name}(BaseModel):'
        )

    excluded_models_pattern = "|".join(excluded_models)
    model_pattern = re.compile(rf'class ({excluded_models_pattern}|BodySearch\w+)\(.*?\):.*?(?=class|$)', re.DOTALL)
    modified_content = re.sub(model_pattern, '', modified_content)
    
    for model in models:
        context_map = {}
        if hasattr(model, "properties"):
            for prop_name, prop in model.properties.items():
                if isinstance(prop, dict) and "x_ontology" in prop:
                    context_map[prop_name] = prop["x_ontology"]

        json_schema_extra = {}

        if hasattr(model, "extensions") and model.extensions:
            json_schema_extra.update(model.extensions)

        if context_map:
            json_schema_extra["@context"] = context_map

        excluded_from_response = []
        if hasattr(model, "properties"):
            for prop_name, prop in model.properties.items():
                if isinstance(prop, dict) and (prop.get("x_exclude_from_response") or prop.get("x-exclude-from-response")):
                    excluded_from_response.append(prop_name)
        if excluded_from_response:
            json_schema_extra["x-exclude-from-response"] = excluded_from_response

        has_enum = False
        if hasattr(model, "properties"):
            for prop_name, prop in model.properties.items():
                if isinstance(prop, dict) and "enum" in prop:
                    has_enum = True
                    break

        if json_schema_extra:
            model_config_line = f"model_config = ConfigDict(json_schema_extra={json_schema_extra})"
            if has_enum:
                model_config_line = f"model_config = ConfigDict(json_schema_extra={json_schema_extra}, use_enum_values=True)"
            modified_content = modified_content.replace(f'class {model.model_name}(LaiaBaseModel):',
                                                        f'class {model.model_name}(LaiaBaseModel):\n    {model_config_line}')
        if hasattr(model, 'extensions') and model.extensions.get('x-auth'):
            modified_content = modified_content.replace(f'class {model.model_name}(LaiaBaseModel):', f'class {model.model_name}(LaiaUser):', 1)

        frontend_fields = []
        if hasattr(model, 'properties'):
            for prop_name, prop in model.properties.items():
                if isinstance(prop, dict) and 'x_frontend_relation' in prop:
                    frontend_fields.append(prop_name)

        if frontend_fields:
            validator_block = f"""
    @field_validator({', '.join([repr(f) for f in frontend_fields])}, mode='before')
    @classmethod
    def convert_objectid_fields(cls, v, info):
        from bson.errors import InvalidId
        try:
            if v is None or v == "" or v == "null":
                return None
            if isinstance(v, list):
                return [ObjectId(x) for x in v if x is not None and x != "" and x != "null"]
            return ObjectId(v)
        except InvalidId as e:
            raise ValueError(f"{{info.field_name}} ==> bson.errors.InvalidId: {{str(e)}}")
    """
            modified_content = re.sub(
                rf'(class {model.model_name}\((?:LaiaBaseModel|LaiaUser)\):)',
                rf'\1{validator_block}',
                modified_content
            )

        for field in frontend_fields:
            modified_content = re.sub(
                rf'({field}\s*:\s*)Optional\[(?:List|list)\[str\]\]',
                rf"\1Optional[List[Annotated[ObjectId, ObjectIdPydanticAnnotation]]]",
                modified_content
            )
            modified_content = re.sub(
                rf'({field}\s*:\s*)(?:List|list)\[str\]',
                rf"\1List[Annotated[ObjectId, ObjectIdPydanticAnnotation]]",
                modified_content
            )
            modified_content = re.sub(
                rf'({field}\s*:\s*)Optional\[str\]',
                rf"\1Optional[Annotated[ObjectId, ObjectIdPydanticAnnotation]]",
                modified_content
            )
            modified_content = re.sub(
                rf'({field}\s*:\s*)str',
                rf"\1Annotated[ObjectId, ObjectIdPydanticAnnotation]",
                modified_content
            )

    modified_content = add_update_models_at_end(modified_content, models)

    with open(output_file, 'w') as f:
        f.write(modified_content)

    with open(output_file, 'r') as f:
        model_content = f.read()

    classes_info = extract_class_info(model_content, models)
    update_file(output_file, classes_info)

    _logger.info(f"File '{output_file}' created and modified.")
