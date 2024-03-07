import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaBaseModel.CreateLaiaBaseModel import create_laia_base_model
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

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
    return db

@pytest_asyncio.fixture
async def repository_instance(in_memory_db):
    return MongoModelRepository(in_memory_db)

class TestCreateLaiaBaseModel:

    @pytest.mark.asyncio
    async def test_create_laia_base_model_success(self, repository_instance):
        new_element = {'name': 'name1', 'description': 'Test Drone', 'weight': 10.5, 'max_altitude': 100.0, 'max_speed': 50.0}
        model = Drone
        user_roles = ['admin']
        result = await create_laia_base_model(new_element, model, user_roles, repository_instance)
        
        assert result.get('name') == new_element.get('name')
        assert result.get('description') == new_element.get('description')
        assert result.get('weight') == new_element.get('weight')
        assert result.get('max_altitude') == new_element.get('max_altitude')
        assert result.get('max_speed') == new_element.get('max_speed')

    @pytest.mark.asyncio
    async def test_create_laia_base_model_without_create_rights(self, repository_instance):
        new_element = {'name': 'name1', 'description': 'Test Drone', 'weight': 10.5, 'max_altitude': 100.0, 'max_speed': 50.0}
        model = Drone
        user_roles = ['user'] 
        with pytest.raises(PermissionError):
            await create_laia_base_model(new_element, model, user_roles, repository_instance)

    @pytest.mark.asyncio
    async def test_create_laia_base_model_missing_parameters(self, repository_instance):
        new_element = {'name': 'name1'} 
        model = Drone
        user_roles = ['admin']
        with pytest.raises(ValueError) as exc_info:
            await create_laia_base_model(new_element, model, user_roles, repository_instance)
        assert "Missing required parameters" in str(exc_info.value)
