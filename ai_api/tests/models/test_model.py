import pytest
import pytest_asyncio
from pymongo import MongoClient
from argapilib.crud_mongo_impl import CRUDMongoImpl
from argapilib.models.AccessRights import AccessRights
from argapilib.models.Role import Role
from argapilib.models.Model import Model

class User(Model):
    description: str
    age: int

class Drone(Model):
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

        with pytest.raises(ValueError, match="Missing required parameters: age"):
            await User.create(new_user, User, user_roles, crud_instance)

    