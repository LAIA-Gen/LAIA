import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaBaseModel.CreateLaiaBaseModel import create_laia_base_model
from laiagenlib.Application.LaiaBaseModel.DeleteLaiaBaseModel import delete_laia_base_model
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

class TestDeleteLaiaBaseModel:

    @pytest.mark.asyncio
    async def test_delete_success(self, repository_instance):
        new_element = {'name': 'name1', 'description': 'Test Drone', 'weight': 10.5, 'max_altitude': 100.0, 'max_speed': 50.0}
        model = Drone
        user_roles = ['admin']
        created_element = await create_laia_base_model(new_element, model, user_roles, repository_instance)
        _logger.info(created_element)
        element_id = created_element['id']

        await delete_laia_base_model(element_id, model, user_roles, repository_instance)

        with pytest.raises(ValueError):
            await repository_instance.get_item(model.__name__.lower(), element_id)

    @pytest.mark.asyncio
    async def test_delete_non_existent_item(self, repository_instance):
        element_id = "non_existent_id"
        model = Drone
        user_roles = ['admin']
        with pytest.raises(ValueError) as exc_info:
            await delete_laia_base_model(element_id, model, user_roles, repository_instance)
        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_access_rights_not_admin(self, repository_instance):
        new_access_rights = {
            "role": "user",
            "model": "drone",
            "operations": {"create": 1, "read": 1, "delete": 1},
            "fields_create": {"name": 1, "description": 1, "weight": 1, "max_altitude": 1, "max_speed": 1},
            "fields_edit": {"name": 1},
            "fields_visible": {"name": 1, "id": 1, "description": 1, "weight": 1, "max_altitude": 1, "max_speed": 1}
        }

        await create_access_rights(repository_instance, new_access_rights, Drone, ["admin"])

        new_element = {'name': 'name1', 'description': 'Test Drone', 'weight': 10.5, 'max_altitude': 100.0, 'max_speed': 50.0}
        model = Drone
        user_roles = ['user'] 
        created_element = await create_laia_base_model(new_element, model, user_roles, repository_instance)
        element_id = str(created_element['id'])

        await delete_laia_base_model(element_id, model, user_roles, repository_instance)
