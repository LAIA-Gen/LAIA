import pytest
import pytest_asyncio
from pymongo import MongoClient
from argapilib.crud_mongo_impl import CRUDMongoImpl
from argapilib.models.AccessRights import AccessRights
from argapilib.models.Role import Role
from argapilib.models.Model import Model

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("access_rights")
    return db

@pytest_asyncio.fixture
async def crud_instance(in_memory_db):
    return CRUDMongoImpl(in_memory_db)

class TestAccessRights:

    @pytest.mark.asyncio
    async def test_create_access_rights_admin_permission(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": {"name": "test_role"},
            "model": {"name": "test_model"},
            "operations": {"create": 1, "read": 1},
            "fields_create": {"field1": 1},
            "fields_edit": {},
            "fields_visible": {"field1": 1}
        }

        created_access_rights = await AccessRights.create(new_access_rights, user_roles, crud_instance)

        assert created_access_rights.role.name == "test_role"
        assert created_access_rights.model.name == "test_model"

    @pytest.mark.asyncio
    async def test_create_access_rights_no_admin_permission(self, crud_instance):
        user_roles = ["user"]
        new_access_rights = {
            "role": {"name": "test_role"},
            "model": {"name": "test_model"},
            "operations": {"create": 1, "read": 1},
            "fields_create": {"field1": 1},
            "fields_edit": {},
            "fields_visible": {"field1": 1}
        }

        with pytest.raises(PermissionError, match="Only users with 'admin' role can create access rights"):
            await AccessRights.create(new_access_rights, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_access_rights_invalid_operations(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": {"name": "test_role"},
            "model": {"name": "test_model"},
            "operations": {"invalid_op": 1},
            "fields_create": {"field1": 1},
            "fields_edit": {},
            "fields_visible": {"field1": 1}
        }

        with pytest.raises(ValueError, match="Invalid format for operation invalid_op"):
            await AccessRights.create(new_access_rights, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_access_rights_invalid_fields_format(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": {"name": "test_role"},
            "model": {"name": "test_model"},
            "operations": {"create": 1, "read": 1},
            "fields_create": "invalid_fields_format",
            "fields_edit": {},
            "fields_visible": {"field1": 1}
        }

        with pytest.raises(ValueError, match="Invalid format for fields_create"):
            await AccessRights.create(new_access_rights, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_access_rights_invalid_field_name(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": {"name": "test_role"},
            "model": {"name": "test_model"},
            "operations": {"create": 1, "read": 1},
            "fields_create": {"invalid_field": 1},
            "fields_edit": {},
            "fields_visible": {"field1": 1}
        }

        with pytest.raises(ValueError, match="Invalid field invalid_field for fields_create"):
            await AccessRights.create(new_access_rights, user_roles, crud_instance)