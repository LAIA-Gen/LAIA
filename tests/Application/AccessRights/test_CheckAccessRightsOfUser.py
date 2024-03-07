import pytest
import pytest_asyncio
from pymongo import MongoClient
from laiagenlib.Application.AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from laiagenlib.Domain.AccessRights.AccessRights import AccessRight
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("accessright")
    return db

@pytest_asyncio.fixture
async def repository_instance(in_memory_db):
    return MongoModelRepository(in_memory_db)

class TestCheckAccessRightsOfUser:

    @pytest.mark.asyncio
    async def test_access_rights_found(self, repository_instance):
        await repository_instance.post_item("accessright", AccessRight(model = "test_model", role = "admin", operations = {"read": 1}))
        await repository_instance.post_item("accessright", AccessRight(model = "test_model", role = "user", operations = {"read": 0}))

        access_rights = await check_access_rights_of_user("test_model", ["admin", "user"], "read", repository_instance)
        
        assert len(access_rights) == 1 

    @pytest.mark.asyncio
    async def test_no_access_rights(self, repository_instance):
        await repository_instance.post_item("accessrights", AccessRight(model = "test_model", role = "user", operations = {"read": 0}))
        
        with pytest.raises(PermissionError):
            await check_access_rights_of_user("test_model", ["user"], "read", repository_instance)

    @pytest.mark.asyncio
    async def test_invalid_model_name(self, repository_instance):
        with pytest.raises(PermissionError):
            await check_access_rights_of_user("invalid_model", ["user"], "read", repository_instance)

    @pytest.mark.asyncio
    async def test_invalid_operation(self, repository_instance):
        with pytest.raises(PermissionError):
            await check_access_rights_of_user("test_model", ["user"], "write", repository_instance)
