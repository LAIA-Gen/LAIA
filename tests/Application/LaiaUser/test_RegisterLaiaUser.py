import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaUser.RegisterLaiaUser import register
from laiagenlib.Application.LaiaUser.CreateLaiaUser import create_laia_user
from laiagenlib.Domain.LaiaUser.LaiaUser import LaiaUser

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("user")
    db.drop_collection("laiauser")
    return db

@pytest_asyncio.fixture
async def repository_instance(in_memory_db):
    return MongoModelRepository(in_memory_db)

class TestRegisterLaiaUser:

    @pytest.mark.asyncio
    async def test_register_laia_user_success(self, repository_instance):
        new_user_data = {
            'name': 'name',
            'email': 'test@example.com',
            'password': 'testpassword',
            'roles': ['admin']
        }
        model = LaiaUser
        user_roles = ['admin']
        
        user = await register(new_user_data, model, user_roles, repository_instance)
        
        assert user['email'] == new_user_data['email']

    @pytest.mark.asyncio
    async def test_register_laia_user_invalid_email(self, repository_instance):
        with pytest.raises(ValueError, match="Invalid email address"):
            await register({'name': 'name', 'email': 'invalidemail.com', 'password': 'StrongPassword123'}, LaiaUser, ['admin'], repository_instance)

    @pytest.mark.asyncio
    async def test_register_laia_user_invalid_password(self, repository_instance):
        with pytest.raises(ValueError, match="Invalid password"):
            await register({'name': 'name', 'email': 'john@example.com', 'password': 'weak'}, LaiaUser, ['admin'], repository_instance)

    @pytest.mark.asyncio
    async def test_register_laia_user_existing_email(self, repository_instance):
        await create_laia_user({'name': 'name', 'email': 'existing@example.com', 'password': 'StrongPassword123'}, LaiaUser, ['admin'], repository_instance)

        with pytest.raises(ValueError, match="User with this email already exists"):
            await register({'name': 'name', 'email': 'existing@example.com', 'password': 'StrongPassword456'}, LaiaUser, ['admin'], repository_instance)