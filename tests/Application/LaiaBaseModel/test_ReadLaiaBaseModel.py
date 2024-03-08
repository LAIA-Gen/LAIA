import pytest
import pytest_asyncio
from bson import ObjectId
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaBaseModel.CreateLaiaBaseModel import create_laia_base_model
from laiagenlib.Application.LaiaBaseModel.ReadLaiaBaseModel import read_laia_base_model
from laiagenlib.Application.AccessRights.CreateAccessRights import create_access_rights
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from laiagenlib.Domain.Shared.Utils.logger import _logger

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
    db.drop_collection("accessright")
    return db

@pytest_asyncio.fixture
async def repository_instance(in_memory_db):
    return MongoModelRepository(in_memory_db)

class TestReadLaiaBaseModel:

    @pytest.mark.asyncio
    async def test_read_success(self, repository_instance):
        new_element = {'name': 'name1', 'description': 'Test Drone', 'weight': 10.5, 'max_altitude': 100.0, 'max_speed': 50.0}
        model = Drone
        user_roles = ['admin']
        created_element = await create_laia_base_model(new_element, model, user_roles, repository_instance)
        element_id = created_element['id']

        retrieved_item = await read_laia_base_model(element_id, model, user_roles, repository_instance)

        assert retrieved_item is not None
        assert retrieved_item['name'] == new_element['name']

    @pytest.mark.asyncio
    async def test_read_without_permission(self, repository_instance):
        new_element = {'name': 'name1', 'description': 'Test Drone', 'weight': 10.5, 'max_altitude': 100.0, 'max_speed': 50.0}
        model = Drone
        user_roles = ['user']
        created_element = await create_laia_base_model(new_element, model, ['admin'], repository_instance)
        element_id = created_element['id']

        with pytest.raises(PermissionError):
            await read_laia_base_model(element_id, model, user_roles, repository_instance)

    @pytest.mark.asyncio
    async def test_read_non_existent_item(self, repository_instance):
        element_id = ObjectId()
        model = Drone
        user_roles = ['admin']
        with pytest.raises(ValueError) as exc_info:
            await read_laia_base_model(element_id, model, user_roles, repository_instance)
