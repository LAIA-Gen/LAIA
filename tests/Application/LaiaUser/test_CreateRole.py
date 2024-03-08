import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaUser.CreateRole import create_role
from laiagenlib.Domain.LaiaUser.Role import Role

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("role")
    return db

@pytest_asyncio.fixture
async def repository_instance(in_memory_db):
    return MongoModelRepository(in_memory_db)

class TestCreateRole:

    @pytest.mark.asyncio
    async def test_create_role_success(self, repository_instance):
        new_role = {'name': 'admin'}
        user_roles = ['admin']
        result = await create_role(new_role, user_roles, repository_instance)
        
        assert result.name == new_role['name']

    @pytest.mark.asyncio
    async def test_create_role_without_admin_rights(self, repository_instance):
        new_role = {'name': 'user'}
        user_roles = ['user'] 
        with pytest.raises(PermissionError):
            await create_role(new_role, user_roles, repository_instance)

    @pytest.mark.asyncio
    async def test_create_role_missing_parameters(self, repository_instance):
        new_role = {} 
        user_roles = ['admin']
        with pytest.raises(ValueError) as exc_info:
            await create_role(new_role, user_roles, repository_instance)
        assert "Missing required parameter: name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_role_already_exists(self, repository_instance):
        existing_role = {'name': 'existing_role'}
        await create_role(existing_role, ['admin'], repository_instance)

        new_role = {'name': 'existing_role'}
        user_roles = ['admin']
        with pytest.raises(ValueError) as exc_info:
            await create_role(new_role, user_roles, repository_instance)
        assert f"Role with name '{new_role['name']}' already exists" in str(exc_info.value)