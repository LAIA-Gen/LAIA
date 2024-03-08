import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaUser.LoginLaiaUser import login
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

class TestLoginLaiaUser:

    @pytest.mark.asyncio
    async def test_login_laia_user_success(self, repository_instance):
        new_user_data = {
            'name': 'name',
            'email': 'test@example.com',
            'password': 'testpassword'
        }
        model = LaiaUser
        await create_laia_user(new_user_data, model, ['admin'], repository_instance)

        user = await login(new_user_data, model, repository_instance)

        assert user['email'] == new_user_data['email']

    @pytest.mark.asyncio
    async def test_login_laia_user_incorrect_email(self, repository_instance):
        new_user_data = {
            'name': 'name',
            'email': 'test@example.com',
            'password': 'testpassword'
        }
        model = LaiaUser
        await create_laia_user(new_user_data, model, ['admin'], repository_instance)

        with pytest.raises(ValueError, match="User not found"):
            await login({'email': 'wrong@example.com', 'password': 'testpassword'}, model, repository_instance)

    @pytest.mark.asyncio
    async def test_login_laia_user_incorrect_password(self, repository_instance):
        new_user_data = {
            'name': 'name',
            'email': 'test@example.com',
            'password': 'testpassword'
        }
        model = LaiaUser
        await create_laia_user(new_user_data, model, ['admin'], repository_instance)

        with pytest.raises(ValueError, match="Incorrect email or password"):
            await login({'email': 'test@example.com', 'password': 'wrongpassword'}, model, repository_instance)

    @pytest.mark.asyncio
    async def test_login_laia_user_missing_email(self, repository_instance):
        with pytest.raises(ValueError, match="Email and password are required for login"):
            await login({'password': 'testpassword'}, LaiaUser, repository_instance)

    @pytest.mark.asyncio
    async def test_login_laia_user_missing_password(self, repository_instance):
        with pytest.raises(ValueError, match="Email and password are required for login"):
            await login({'email': 'test@example.com'}, LaiaUser, repository_instance)