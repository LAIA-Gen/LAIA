import pytest
import pytest_asyncio
import bcrypt
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
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

class TestCreateLaiaUser:

    @pytest.mark.asyncio
    async def test_create_laia_user_success(self, repository_instance):
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
        
        user = await create_laia_user(new_element, model, user_roles, repository_instance)
        
        assert user['email'] == new_element['email']
        assert bcrypt.checkpw(new_element['password'].encode('utf-8'), user['password'].encode('utf-8'))
        assert user['roles'] == user_roles

    @pytest.mark.asyncio
    async def test_create_laia_user_invalid_email(self, repository_instance):
        with pytest.raises(ValueError, match="Invalid email address"):
            await create_laia_user({'name': 'name', 'email': 'invalidemail.com', 'password': 'StrongPassword123'}, LaiaUser, ['admin'], repository_instance)

    @pytest.mark.asyncio
    async def test_create_laia_user_invalid_password(self, repository_instance):
        with pytest.raises(ValueError, match="Invalid password"):
            await create_laia_user({'name': 'name', 'email': 'john@example.com', 'password': 'weak'}, LaiaUser, ['admin'], repository_instance)

    @pytest.mark.asyncio
    async def test_create_laia_user_existing_email(self, repository_instance):
        await create_laia_user({'name': 'name', 'email': 'existing@example.com', 'password': 'StrongPassword123'}, LaiaUser, ['admin'], repository_instance)

        with pytest.raises(ValueError, match="User with this email already exists"):
            await create_laia_user({'name': 'name', 'email': 'existing@example.com', 'password': 'StrongPassword456'}, LaiaUser, ['admin'], repository_instance)