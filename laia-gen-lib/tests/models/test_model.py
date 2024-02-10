import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.crud.crud_mongo_impl import CRUDMongoImpl
from laiagenlib.models.Model import LaiaBaseModel
from laiagenlib.models.AccessRights import AccessRights
from laiagenlib.utils.logger import _logger

class User(LaiaBaseModel):
    description: str
    age: int

class Drone(LaiaBaseModel):
    description: str
    weight: float
    max_altitude: float
    max_speed: float

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("user")
    db.drop_collection("drone")
    db.drop_collection("accessrights")
    return db

@pytest_asyncio.fixture
async def crud_instance(in_memory_db):
    return CRUDMongoImpl(in_memory_db)

class TestModel:

    @pytest.mark.asyncio
    async def test_model_created_by_admin(self, crud_instance):
        user_roles = ["admin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }
        await User.create(new_user, User, user_roles, crud_instance)
    
    @pytest.mark.asyncio
    async def test_create_element_missing_parameters_raises_exception(self, crud_instance):
        user_roles = ["admin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
        }

        with pytest.raises(ValueError, match="Missing required parameters"):
            await User.create(new_user, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_element_missing_access_rights(self, crud_instance):
        user_roles = ["userAdmin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }

        with pytest.raises(PermissionError, match="None of the roles have sufficient permissions for operation 'create' on model 'user'"):
            await User.create(new_user, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_element_missing_access_rights_create_operation(self, crud_instance):
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"read": 1},
            "fields_create": {"description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        await AccessRights.create(new_access_rights, User, ["admin"], crud_instance)
        
        user_roles = ["userAdmin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }

        with pytest.raises(PermissionError, match="None of the roles have sufficient permissions for operation 'create' on model 'user'"):
            await User.create(new_user, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_element_missing_access_rights_specific_field(self, crud_instance):
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"name": 1, "description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        await AccessRights.create(new_access_rights, User, ["admin"], crud_instance)
        
        user_roles = ["userAdmin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }

        with pytest.raises(PermissionError, match="Insufficient permissions to create the field 'age' in any role."):
            await User.create(new_user, User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_element_with_different_role(self, crud_instance):
        new_access_rights1 = {
            "role": "userAdmin1",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"name": 1, "description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        new_access_rights2 = {
            "role": "userAdmin2",
            "model": "user",
            "operations": {"create": 1, "read": 1},
            "fields_create": {"name": 1, "description": 1, "age": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }


        await AccessRights.create(new_access_rights1, User, ["admin"], crud_instance)
        await AccessRights.create(new_access_rights2, User, ["admin"], crud_instance)
        
        user_roles = ["userAdmin1", "userAdmin2"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }

        user = await User.create(new_user, User, user_roles, crud_instance)

        assert user is not None
        assert user["description"] == "This is a description"

    @pytest.mark.asyncio
    async def test_model_updated_by_admin(self, crud_instance):
        user_roles = ["admin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }
        
        user = await User.create(new_user, User, user_roles, crud_instance)
        
        updated_user = await User.update(user["id"], {"name": "blanca"}, User, user_roles, crud_instance)

        assert updated_user is not None
        assert updated_user["name"] == "blanca"
        assert updated_user["description"] == user["description"]
        assert updated_user["age"] == user["age"]
        assert updated_user["id"] == user["id"]

    @pytest.mark.asyncio
    async def test_read_element_missing_access_rights_read_operation(self, crud_instance):
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "update": 1},
            "fields_create": {"name": 1, "description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        await AccessRights.create(new_access_rights, User, ["admin"], crud_instance)
        
        user_roles = ["userAdmin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }
        
        user = await User.create(new_user, User, ["admin"], crud_instance)

        with pytest.raises(PermissionError, match="None of the roles have sufficient permissions for operation 'read' on model 'user'"):
            await User.read(user["id"], User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_read_element_missing_access_rights_specific_field(self, crud_instance):
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "read": 1, "update": 1},
            "fields_create": {"name": 1, "description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        await AccessRights.create(new_access_rights, User, ["admin"], crud_instance)
        
        user_roles = ["userAdmin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }
        
        user = await User.create(new_user, User, ["admin"], crud_instance)

        user_read = await User.read(user["id"], User, user_roles, crud_instance)

        assert user_read == {"description": "This is a description"}

    @pytest.mark.asyncio
    async def test_delete_element(self, crud_instance): 
        user_roles = ["admin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }
        
        user = await User.create(new_user, User, user_roles, crud_instance)

        await User.delete(user["id"], User, user_roles, crud_instance)

        with pytest.raises(ValueError, match=f"user with ID {user['id']} not found"):
            await User.read(user["id"], User, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_delete_element_missing_access_rights_delete_operation(self, crud_instance):
        new_access_rights = {
            "role": "userAdmin",
            "model": "user",
            "operations": {"create": 1, "update": 1},
            "fields_create": {"name": 1, "description": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"description": 1}
        }

        await AccessRights.create(new_access_rights, User, ["admin"], crud_instance)
        
        user_roles = ["userAdmin"]
        new_user = {
            "name": "alba",
            "description": "This is a description",
            "age": 21
        }
        
        user = await User.create(new_user, User, ["admin"], crud_instance)

        with pytest.raises(PermissionError, match="None of the roles have sufficient permissions for operation 'delete' on model 'user'"):
            await User.delete(user["id"], User, user_roles, crud_instance)