import pytest, pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from laiagenlib.Domain.Shared.Utils.logger import _logger

class User(LaiaBaseModel):
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
    return MongoModelRepository(in_memory_db)

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

    @pytest.mark.asyncio
    async def test_filter_by_id(self, crud_instance):
        item_ids = []
        for _ in range(5):
            created_item = await crud_instance.post_item("user_collection", User(**test_data))
            item_ids.append(created_item["id"])

        query_id = item_ids[0]
        items, _ = await crud_instance.get_items("user_collection", filters={"id": query_id})
        assert len(items) == 1
        assert items[0]["id"] == query_id

        query_id = item_ids[0]
        items, _ = await crud_instance.get_items("user_collection", filters={"id": {"$in": [query_id]}})
        assert len(items) == 1
        assert items[0]["id"] == query_id

        query_ids = item_ids[1:3]
        items, _ = await crud_instance.get_items("user_collection", filters={"id": {"$in": query_ids}})
        assert len(items) == 2
        retrieved_ids = [item["id"] for item in items]
        assert all(query_id in retrieved_ids for query_id in query_ids)

        query_ids = item_ids[:3]
        items, _ = await crud_instance.get_items("user_collection", filters={"id": {"$nin": query_ids}})
        assert len(items) == 2 
        retrieved_ids = [item["id"] for item in items]
        assert all(query_id not in retrieved_ids for query_id in query_ids)