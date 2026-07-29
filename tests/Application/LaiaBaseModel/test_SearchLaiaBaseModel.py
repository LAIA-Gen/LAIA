import pytest
import pytest_asyncio
from pymongo import MongoClient
from pydantic import Field
from bson import ObjectId
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaBaseModel.SearchLaiaBaseModel import search_laia_base_model
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from laiagenlib.Domain.Shared.Utils.ModelRegistry import register_model

class User(LaiaBaseModel):
    name: str = ""
    description: str
    age: int

class Drone(LaiaBaseModel):
    name: str = ""
    description: str
    weight: float
    max_altitude: float
    max_speed: float


class Offer(LaiaBaseModel):
    userId: str = Field(
        "",
        x_frontend_relation="User",
        populate={"excludeFields": ["email", "telephone", "password"]},
    )

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("user")
    db.drop_collection("drone")
    db.drop_collection("accessright")
    db.drop_collection("publicoffer")
    db.drop_collection("offer")
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

    @pytest.mark.asyncio
    async def test_search_laia_base_model_public(self, repository_instance):
        class PublicOffer(LaiaBaseModel):
            name: str = ""
            description: str
            model_config = {
                "json_schema_extra": {
                    "x-permissions": {
                        "search": []
                    }
                }
            }

        await repository_instance.post_item("publicoffer", PublicOffer(name="Offer 1", description="Public Offer 1"))

        skip = 0
        limit = 10
        filters = {}
        orders = {}

        model = PublicOffer
        user_roles = []
        result = await search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository_instance)

        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "Offer 1"

    @pytest.mark.asyncio
    async def test_populate_excludes_relation_sensitive_fields(self, repository_instance):
        user = await repository_instance.post_item(
            "user",
            User(
                name="Volunteer",
                description="Available",
                age=30,
            ),
        )
        repository_instance.db["user"].update_one(
            {"_id": ObjectId(user["id"])},
            {
                "$set": {
                    "email": "volunteer@example.com",
                    "telephone": "600000000",
                    "password": "secret",
                }
            },
        )
        await repository_instance.post_item("offer", Offer(userId=user["id"]))
        register_model("user", User)

        result = await search_laia_base_model(
            0,
            10,
            {},
            {},
            Offer,
            ["admin"],
            repository_instance,
            populate=[{"id": "userId", "from": "user", "as": "user"}],
        )

        populated_user = result["items"][0]["user"]
        assert populated_user["name"] == "Volunteer"
        assert "email" not in populated_user
        assert "telephone" not in populated_user
        assert "password" not in populated_user

