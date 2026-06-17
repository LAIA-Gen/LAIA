from importlib.util import module_from_spec, spec_from_file_location
from typing import Annotated

import pytest
from bson import ObjectId
from pydantic import BaseModel, ValidationError

from laiagenlib.Domain.Shared.Types.objectid_annotation import ObjectIdPydanticAnnotation


class ModelWithObjectId(BaseModel):
    value: Annotated[ObjectId, ObjectIdPydanticAnnotation]


def test_import_objectid_annotation():
    assert ObjectIdPydanticAnnotation is not None


def test_objectid_annotation_validates_and_serializes_with_pydantic_v2():
    object_id = ObjectId()

    model_from_object_id = ModelWithObjectId(value=object_id)
    model_from_string = ModelWithObjectId(value=str(object_id))

    assert model_from_object_id.value == object_id
    assert model_from_string.value == object_id
    assert model_from_string.model_dump(mode="json") == {"value": str(object_id)}
    assert model_from_string.model_dump_json() == f'{{"value":"{object_id}"}}'


def test_objectid_annotation_rejects_invalid_values():
    with pytest.raises(ValidationError):
        ModelWithObjectId(value="not-an-object-id")


def test_generated_backend_models_file_can_import_objectid_annotation(tmp_path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        "from typing import Annotated\n"
        "from bson import ObjectId\n"
        "from pydantic import BaseModel\n"
        "from laiagenlib.Domain.Shared.Types.objectid_annotation import ObjectIdPydanticAnnotation\n\n"
        "class GeneratedModel(BaseModel):\n"
        "    value: Annotated[ObjectId, ObjectIdPydanticAnnotation]\n",
        encoding="utf-8",
    )

    spec = spec_from_file_location("generated_models", models_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    object_id = ObjectId()
    model = module.GeneratedModel(value=str(object_id))
    assert model.value == object_id
