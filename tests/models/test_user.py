import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.crud.crud_mongo_impl import CRUDMongoImpl
from laiagenlib.models.User import LaiaUser

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("user")
    return db

@pytest_asyncio.fixture
async def crud_instance(in_memory_db):
    return CRUDMongoImpl(in_memory_db)

class TestLaiaUser:

    @pytest.mark.asyncio
    async def test_user_create(self, crud_instance):
        new_user_data = {
            'email': 'test@example.com',
            'password': 'testpassword'
        }
        user = await LaiaUser.register(new_user_data, crud_instance)
        assert user.email == 'test@example.com'
        assert user.password != 'testpassword'

    @pytest.mark.asyncio
    async def test_update_user(self, crud_instance):
        new_user_data = {
            'email': 'test@example.com',
            'password': 'testpassword'
        }
        user = await LaiaUser.register(new_user_data, crud_instance)

        updated_values = {'email': 'updated@example.com'}
        updated_user = await LaiaUser.update(user.id, updated_values, LaiaUser, [], crud_instance)

        assert updated_user.email == 'updated@example.com'
        assert updated_user.password != 'testpassword'

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, crud_instance):
        with pytest.raises(ValueError):
            await LaiaUser.register({'email': 'invalidemail', 'password': 'testpassword'}, crud_instance)

    @pytest.mark.asyncio
    async def test_register_user_invalid_password(self, crud_instance):
        with pytest.raises(ValueError):
            await LaiaUser.register({'email': 'test@example.com', 'password': 'short'}, crud_instance)

    @pytest.mark.asyncio
    async def test_login_user(self, crud_instance):
        new_user_data = {
            'email': 'test@example.com',
            'password': 'testpassword'
        }
        await LaiaUser.register(new_user_data, crud_instance)

        logged_in_user = await LaiaUser.login('test@example.com', 'testpassword', crud_instance)
        assert logged_in_user is not None

        with pytest.raises(ValueError):
            await LaiaUser.login('test@example.com', 'wrongpassword', crud_instance)

        with pytest.raises(ValueError):
            await LaiaUser.login('nonexistent@example.com', 'testpassword', crud_instance)