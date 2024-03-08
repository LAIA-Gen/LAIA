import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaBaseModel.SearchLaiaBaseModel import search_laia_base_model
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
    db.drop_collection("accessright")
    return db

@pytest_asyncio.fixture
async def repository_instance(in_memory_db):
    return MongoModelRepository(in_memory_db)

class TestSearchLaiaBaseModel:
    @pytest.mark.asyncio
    async def test_search_laia_base_model_success(self, repository_instance):
        await repository_instance.post_item("drone", Drone(name="Drone 1", description="Test Drone 1", weight=10.5, max_altitude=100.0, max_speed=50.0))
        await repository_instance.post_item("drone", Drone(name="Drone 2", description="Test Drone 2", weight=12.5, max_altitude=120.0, max_speed=52.0))

        skip = 0
        limit = 10
        filters = {"description": "Test Drone 1"}
        orders = {}

        model = Drone
        user_roles = ['admin']
        result = await search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository_instance)

        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "Drone 1"
        assert result["items"][0]["description"] == "Test Drone 1"

    @pytest.mark.asyncio
    async def test_search_laia_base_model_pagination(self, repository_instance):
        for i in range(15):
            await repository_instance.post_item("drone", Drone(name=f"Drone {i}", description=f"Test Drone {i}", weight=10.5, max_altitude=100.0, max_speed=50.0))

        skip = 0
        limit = 10
        filters = {}
        orders = {}

        model = Drone
        user_roles = ['admin']
        result = await search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository_instance)

        assert len(result["items"]) == 10
        assert result["current_page"] == 1
        assert result["max_pages"] == 2

    @pytest.mark.asyncio
    async def test_search_laia_base_model_access_rights(self, repository_instance):
        skip = 0
        limit = 10
        filters = {}
        orders = {}

        model = Drone
        user_roles = ['user']
        with pytest.raises(PermissionError):
            await search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository_instance)
