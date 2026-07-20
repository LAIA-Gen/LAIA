import pytest
import pytest_asyncio
from pymongo import MongoClient
from bson import ObjectId
from pydantic import ConfigDict
from fastapi import HTTPException
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository
from laiagenlib.Application.LaiaBaseModel.UpdateLaiaBaseModel import update_laia_base_model
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

class Offer(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={"x-owner-fields": ["owner", "acceptedUserIds"]})

    originText: str
    acceptedUserIds: list = []

class FullProtectedOffer(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "preupdate": [
                {
                    "script": {
                        "condition": "statusOffer == 'full'",
                        "execute": "HttpResponse({status: 409, body: 'Offer is full'})",
                    },
                }
            ]
        }
    })

    originText: str
    statusOffer: str = "active"

class CalculatedOffer(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "postupdate": [
                {
                    "script": {
                        "condition": "true",
                        "execute": "totalSeatsOccupied = len(acceptedUserIds)",
                    },
                },
                {
                    "script": {
                        "condition": "{{totalSeatsOccupied}} == {{totalSeats}}",
                        "execute": "statusOffer = 'full'",
                    },
                },
            ]
        }
    })

    originText: str
    acceptedUserIds: list = []
    totalSeatsOccupied: int = 0
    totalSeats: int = 0
    statusOffer: str = "active"

class QueryCalculatedOffer(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "postupdate": [
                {
                    "script": {
                        "condition": "true",
                        "execute": "acceptedUserIds = QUERY(Match.offerId == {{id}} && Match.status == 'confirmed').initiated_by",
                    },
                },
                {
                    "script": {
                        "condition": "true",
                        "execute": "totalSeatsOccupied = len(acceptedUserIds)",
                    },
                },
                {
                    "script": {
                        "condition": "{{totalSeatsOccupied}} == {{totalSeats}}",
                        "execute": "statusOffer = 'full'",
                    },
                },
            ]
        }
    })

    originText: str
    acceptedUserIds: list = []
    totalSeatsOccupied: int = 0
    totalSeats: int = 0
    statusOffer: str = "active"

@pytest.fixture
def in_memory_db():
    client = MongoClient()
    db = client["testdb"]
    db.drop_collection("user")
    db.drop_collection("drone")
    db.drop_collection("offer")
    db.drop_collection("fullprotectedoffer")
    db.drop_collection("calculatedoffer")
    db.drop_collection("querycalculatedoffer")
    db.drop_collection("match")
    db.drop_collection("accessright")
    return db

@pytest_asyncio.fixture
async def repository_instance(in_memory_db):
    return MongoModelRepository(in_memory_db)

class TestUpdateLaiaBaseModel:

    @pytest.mark.asyncio
    async def test_update_laia_base_model_success(self, repository_instance):
        drone = await repository_instance.post_item("drone", {"description": "Test Drone", "weight": 10.5, "max_altitude": 100.0, "max_speed": 50.0})
        drone_id = drone['id']
        updated_values = {"description": "Updated Drone Description"}

        model = Drone 
        user_roles = ['admin']
        updated_element = await update_laia_base_model(drone_id, updated_values, model, user_roles, repository_instance)

        assert updated_element["description"] == "Updated Drone Description"

    @pytest.mark.asyncio
    async def test_update_laia_base_model_without_edit_rights(self, repository_instance):
        drone = await repository_instance.post_item("drone", {"description": "Test Drone", "weight": 10.5, "max_altitude": 100.0, "max_speed": 50.0})
        drone_id = drone['id']
        updated_values = {"description": "Updated Drone Description"}

        model = Drone
        user_roles = ['user']
        with pytest.raises(PermissionError):
            await update_laia_base_model(drone_id, updated_values, model, user_roles, repository_instance)

    @pytest.mark.asyncio
    async def test_update_laia_base_model_non_existent_element(self, repository_instance):
        non_existent_element_id = ObjectId()

        updated_values = {"description": "Updated Drone Description"}

        model = Drone
        user_roles = ['admin']
        with pytest.raises(ValueError):
            await update_laia_base_model(non_existent_element_id, updated_values, model, user_roles, repository_instance)

    @pytest.mark.asyncio
    async def test_update_with_owner_fields_allows_accepted_user_when_access_rights_disabled(self, repository_instance):
        owner_id = ObjectId()
        accepted_user_id = ObjectId()
        offer = await repository_instance.post_item("offer", {
            "owner": owner_id,
            "originText": "Original",
            "acceptedUserIds": [accepted_user_id],
        })

        updated_element = await update_laia_base_model(
            offer["id"],
            {"originText": "Modified by accepted user"},
            Offer,
            [],
            repository_instance,
            use_access_rights=False,
            user_id=str(accepted_user_id),
        )

        assert updated_element["originText"] == "Modified by accepted user"

    @pytest.mark.asyncio
    async def test_update_with_owner_fields_blocks_intruder_when_access_rights_disabled(self, repository_instance):
        owner_id = ObjectId()
        accepted_user_id = ObjectId()
        intruder_id = ObjectId()
        offer = await repository_instance.post_item("offer", {
            "owner": owner_id,
            "originText": "Original",
            "acceptedUserIds": [accepted_user_id],
        })

        with pytest.raises(PermissionError):
            await update_laia_base_model(
                offer["id"],
                {"originText": "Intruder update"},
                Offer,
                [],
                repository_instance,
                use_access_rights=False,
                user_id=str(intruder_id),
            )

    @pytest.mark.asyncio
    async def test_preupdate_hook_can_block_update_with_http_409(self, repository_instance):
        offer = await repository_instance.post_item("fullprotectedoffer", {
            "originText": "Original",
            "statusOffer": "full",
        })

        with pytest.raises(HTTPException) as exc_info:
            await update_laia_base_model(
                offer["id"],
                {"originText": "Should not be saved"},
                FullProtectedOffer,
                ["admin"],
                repository_instance,
            )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Offer is full"
        stored = await repository_instance.get_item("fullprotectedoffer", offer["id"])
        assert stored["originText"] == "Original"

    @pytest.mark.asyncio
    async def test_postupdate_hook_calculates_total_seats_from_accepted_users(self, repository_instance):
        user_1 = str(ObjectId())
        user_2 = str(ObjectId())
        offer = await repository_instance.post_item("calculatedoffer", {
            "originText": "Original",
            "acceptedUserIds": [],
            "totalSeatsOccupied": 0,
            "totalSeats": 2,
            "statusOffer": "active",
        })

        updated = await update_laia_base_model(
            offer["id"],
            {"acceptedUserIds": [user_1, user_2]},
            CalculatedOffer,
            ["admin"],
            repository_instance,
        )

        assert updated["acceptedUserIds"] == [user_1, user_2]
        assert updated["totalSeatsOccupied"] == 2
        assert updated["statusOffer"] == "full"

    @pytest.mark.asyncio
    async def test_postupdate_hook_can_calculate_accepted_users_from_match_query(self, repository_instance):
        user_1 = str(ObjectId())
        user_2 = str(ObjectId())
        ignored_user = str(ObjectId())
        offer = await repository_instance.post_item("querycalculatedoffer", {
            "originText": "Original",
            "acceptedUserIds": [],
            "totalSeatsOccupied": 0,
            "totalSeats": 2,
            "statusOffer": "active",
        })
        await repository_instance.post_item("match", {
            "offerId": offer["id"],
            "status": "confirmed",
            "initiated_by": user_1,
        })
        await repository_instance.post_item("match", {
            "offerId": offer["id"],
            "status": "confirmed",
            "initiated_by": user_2,
        })
        await repository_instance.post_item("match", {
            "offerId": offer["id"],
            "status": "pending_confirmation",
            "initiated_by": ignored_user,
        })

        updated = await update_laia_base_model(
            offer["id"],
            {"originText": "Recalculated"},
            QueryCalculatedOffer,
            ["admin"],
            repository_instance,
        )

        assert updated["acceptedUserIds"] == [user_1, user_2]
        assert updated["totalSeatsOccupied"] == 2
        assert updated["statusOffer"] == "full"
