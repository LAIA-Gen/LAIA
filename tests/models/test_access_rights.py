import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.crud.crud_mongo_impl import CRUDMongoImpl
from laiagenlib.models.AccessRights import AccessRight
from laiagenlib.models.Model import LaiaBaseModel

class User(LaiaBaseModel):
    description: str
    age: int

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("accessrights")
    return db

@pytest_asyncio.fixture
async def crud_instance(in_memory_db):
    return CRUDMongoImpl(in_memory_db)

class TestAccessRights:

    @pytest.mark.asyncio
    async def test_model_name_different_that_model_raises_exception(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": "owner",
            "model": "drone",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"description": 1},
            "fields_edit": {},
            "fields_visible": {"description": 1}
        }

        with pytest.raises(ValueError, match="Provided model name does not match the class model name"):
            await AccessRight.create(new_access_rights, User, user_roles, crud_instance)
    
    @pytest.mark.asyncio
    async def test_create_access_rights_no_admin_permission_raises_exception(self, crud_instance):
        user_roles = ["user"]
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"description": 1},
            "fields_edit": {},
            "fields_visible": {"description": 1}
        }

        with pytest.raises(PermissionError, match="Only users with 'admin' role can create access rights"):
            await AccessRight.create(new_access_rights, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_access_rights_admin_permission(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        created_access_rights = await AccessRight.create(new_access_rights, User, user_roles, crud_instance)

        assert created_access_rights.role == "userAdmin"
        assert created_access_rights.model == "user"

    @pytest.mark.asyncio
    async def test_create_access_rights_admin_permission(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": "userAdmin",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        with pytest.raises(ValueError, match="Missing required parameters"):
            await AccessRight.create(new_access_rights, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_access_rights_invalid_operations(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"invalid_op": 1},
            "fields_create": {"description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        with pytest.raises(ValueError, match="Invalid format for operation invalid_op"):
            await AccessRight.create(new_access_rights, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_access_rights_invalid_fields_format(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": "invalid_format",
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        with pytest.raises(ValueError, match="Invalid format for fields_create"):
            await AccessRight.create(new_access_rights, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_access_rights_invalid_field_name(self, crud_instance):
        user_roles = ["admin"]
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"invalid_field": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        with pytest.raises(ValueError, match="Invalid field invalid_field for fields_create"):
            await AccessRight.create(new_access_rights, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_access_rights_already_exists(self, crud_instance):
        user_roles = ["admin"]
        existing_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        await AccessRight.create(existing_access_rights, User, user_roles, crud_instance)

        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        with pytest.raises(ValueError, match="AccessRights with the same role and model already exists"):
            await AccessRight.create(new_access_rights, User, user_roles, crud_instance)