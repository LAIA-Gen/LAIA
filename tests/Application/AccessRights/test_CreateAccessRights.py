import pytest
import pytest_asyncio
from pymongo import MongoClient
from pydantic import BaseModel
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.AccessRights.CreateAccessRights import create_access_rights
from laiagenlib.Domain.AccessRights.AccessRights import AccessRight

class ExampleModel(BaseModel):
    field1: int
    field2: int

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("accessright")
    return db

@pytest_asyncio.fixture
async def repository_instance(in_memory_db):
    return MongoModelRepository(in_memory_db)

class TestCreateAccessRights:

    @pytest.mark.asyncio
    async def test_create_access_rights_success(self, repository_instance):
        new_access_rights = {
            "role": "admin",
            "model": "examplemodel",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"field1": 1},
            "fields_edit": {"field1": 1},
            "fields_visible": {"field1": 1}
        }

        created_accessrights = await create_access_rights(repository_instance, new_access_rights, ExampleModel, ["admin", "user"])

        assert created_accessrights is not None
        assert created_accessrights.get('operations') == new_access_rights.get('operations')
        assert created_accessrights.get('fields_create') == new_access_rights.get('fields_create')

    @pytest.mark.asyncio
    async def test_create_access_rights_invalid_role(self, repository_instance):
        new_access_rights = {
            "role": "user",
            "model": "examplemodel",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"field1": 1},
            "fields_edit": {"field1": 1},
            "fields_visible": {"field1": 1}
        }

        with pytest.raises(PermissionError):
            await create_access_rights(repository_instance, new_access_rights, ExampleModel, ["user"])

    @pytest.mark.asyncio
    async def test_create_access_rights_existing_rights(self, repository_instance):
        existing_access_rights = AccessRight(
            role="admin",
            model="examplemodel",
            operations={"create": 1, "read": 1},
            fields_create={"field1": 1},
            fields_edit={"field1": 1},
            fields_visible={"field1": 1}
        )
        await repository_instance.post_item("accessright", existing_access_rights.model_dump())

        new_access_rights = {
            "role": "admin",
            "model": "examplemodel",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"field1": 1},
            "fields_edit": {"field1": 1},
            "fields_visible": {"field1": 1}
        }

        with pytest.raises(ValueError):
            await create_access_rights(repository_instance, new_access_rights, ExampleModel, ["admin"])

    @pytest.mark.asyncio
    async def test_create_access_rights_invalid_field(self, repository_instance):
        new_access_rights = {
            "role": "admin",
            "model": "examplemodel",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"field3": 1}, 
            "fields_edit": {"field1": 1},
            "fields_visible": {"field1": 1}
        }

        with pytest.raises(ValueError):
            await create_access_rights(repository_instance, new_access_rights, ExampleModel, ["admin"])