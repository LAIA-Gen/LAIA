import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaUser.UpdateLaiaUser import update_laia_user
from laiagenlib.Application.LaiaUser.CreateLaiaUser import create_laia_user
from laiagenlib.Domain.LaiaUser.LaiaUser import LaiaUser

class User(LaiaUser):
    description: str
    age: int

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

class TestUpdateLaiaUser:

    @pytest.mark.asyncio
    async def test_update_laia_user_success(self, repository_instance):
        new_element = {
            'name': 'name',
            'email': 'test@example.com',
            'password': 'testpassword',
            'roles': ['admin'],
            'description': 'testdescription',
            'age': 12
        }
        model = User
        user_roles = ['admin']
        
        created_user = await create_laia_user(new_element, model, user_roles, repository_instance)

        updated_values = {
            'name': 'new name',
            'email': 'newemail@example.com',
            'password': 'newpassword',
            'roles': ['user'],
            'description': 'new description',
            'age': 25
        }
        
        updated_user = await update_laia_user(created_user['id'], updated_values, model, user_roles, repository_instance)
        
        assert updated_user['name'] == updated_values['name']
        assert updated_user['email'] == updated_values['email']

    @pytest.mark.asyncio
    async def test_update_laia_user_invalid_email(self, repository_instance):
        new_element = {
            'name': 'name',
            'email': 'test@example.com',
            'password': 'testpassword',
            'roles': ['admin'],
            'description': 'testdescription',
            'age': 12
        }
        model = User
        user_roles = ['admin']
        
        created_user = await create_laia_user(new_element, model, user_roles, repository_instance)

        with pytest.raises(ValueError, match="Invalid email address"):
            await update_laia_user(created_user['id'], {'email': 'invalidemail.com'}, model, user_roles, repository_instance)

    @pytest.mark.asyncio
    async def test_update_laia_user_existing_email(self, repository_instance):
        new_element = {
            'name': 'name',
            'email': 'test@example.com',
            'password': 'testpassword',
            'roles': ['admin'],
            'description': 'testdescription',
            'age': 12
        }
        model = User
        user_roles = ['admin']
        
        created_user = await create_laia_user(new_element, model, user_roles, repository_instance)

        with pytest.raises(ValueError, match="User with this email already exists"):
            await update_laia_user(created_user['id'], {'email': 'test@example.com'}, model, user_roles, repository_instance)

    @pytest.mark.asyncio
    async def test_update_laia_user_invalid_password(self, repository_instance):
        new_element = {
            'name': 'name',
            'email': 'test@example.com',
            'password': 'testpassword',
            'roles': ['admin'],
            'description': 'testdescription',
            'age': 12
        }
        model = User
        user_roles = ['admin']
        
        created_user = await create_laia_user(new_element, model, user_roles, repository_instance)

        with pytest.raises(ValueError, match="Invalid password"):
            await update_laia_user(created_user['id'], {'password': 'weak'}, model, user_roles, repository_instance)