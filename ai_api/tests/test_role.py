import pytest
import pytest_asyncio
from pymongo import MongoClient
from argapilib.crud_mongo_impl import CRUDMongoImpl
from argapilib.Role import Role

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("role")
    return db

@pytest_asyncio.fixture
async def crud_instance(in_memory_db):
    return CRUDMongoImpl(in_memory_db)

class TestRole:

    @pytest.mark.asyncio
    async def test_create_role_without_name_raises_exception(self, crud_instance):
        user_roles = ["admin"]
        new_role = {"something": "test_role"}

        with pytest.raises(ValueError, match="Missing required parameter: name"):
            await Role.create(new_role, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_role_admin_permission(self, crud_instance):
        user_roles = ["admin"]
        new_role = {"name": "test_role"}

        created_role = await Role.create(new_role, user_roles, crud_instance)

        assert created_role.name == "test_role"
        
        found_roles, _ = await crud_instance.get_items("role", filters={"name": "test_role"})

        assert len(found_roles) == 1
        assert found_roles[0]["name"] == "test_role"

    @pytest.mark.asyncio
    async def test_create_role_different_permission(self, crud_instance):
        user_roles = ["user"]
        new_role = {"name": "test_role"}

        with pytest.raises(PermissionError, match="Only users with 'admin' role can create new roles"):
            await Role.create(new_role, user_roles, crud_instance)

    @pytest.mark.asyncio
    async def test_create_role_duplicate_name(self, crud_instance):
        user_roles = ["admin"]
        new_role = {"name": "test_role"}

        await Role.create(new_role, user_roles, crud_instance)

        with pytest.raises(ValueError, match=f"Role with name '{new_role['name']}' already exists"):
            await Role.create(new_role, user_roles, crud_instance)