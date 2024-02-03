import pytest, pytest_asyncio
from pymongo import MongoClient
from argapilib.crud_mongo_impl import CRUDMongoImpl
from argapilib.models.Model import Model

class User(Model):
    description: str
    age: int

test_data = {
    "name": "Test Item",
    "description": "This is a test description",
    "age": 21
}

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("user_collection")
    return db

@pytest_asyncio.fixture
async def crud_instance(in_memory_db):
    return CRUDMongoImpl(in_memory_db)

class TestCRUDMongoImpl:

    @pytest.mark.asyncio
    async def test_post_item(self, crud_instance):
        created_item = await crud_instance.post_item("user_collection", User(**test_data))
        assert "id" in created_item
        assert created_item["name"] == test_data["name"]

    @pytest.mark.asyncio
    async def test_get_item(self, crud_instance):
        created_item = await crud_instance.post_item("user_collection", User(**test_data))

        retrieved_item = await crud_instance.get_item("user_collection", created_item["id"])
        assert retrieved_item["name"] == test_data["name"]

    @pytest.mark.asyncio
    async def test_put_item(self, crud_instance):
        created_item = await crud_instance.post_item("user_collection", User(**test_data))

        update_fields = {"name": "Updated Item"}
        updated_item = await crud_instance.put_item("user_collection", created_item["id"], update_fields)

        assert updated_item["name"] == update_fields["name"]

    @pytest.mark.asyncio
    async def test_delete_item(self, crud_instance):
        created_item = await crud_instance.post_item("user_collection", User(**test_data))

        deleted_item = await crud_instance.delete_item("user_collection", created_item["id"])

        assert deleted_item["id"] == created_item["id"]

    @pytest.mark.asyncio
    async def test_get_items(self, crud_instance):
        for _ in range(5):
            await crud_instance.post_item("user_collection", User(**test_data))

        items, total_count = await crud_instance.get_items("user_collection")

        assert len(items) == 5
        assert total_count == 5