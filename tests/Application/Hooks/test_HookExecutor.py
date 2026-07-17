import pytest
from pydantic import ConfigDict

from laiagenlib.Application.Hooks.HookExecutor import execute_hooks
from laiagenlib.Domain.Hooks.LambdaRegistry import register_lambda
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel


class FakeRepository:
    def __init__(self):
        self.items = {
            "offer": [{"id": "offer-1", "userId": "user-1"}],
            "user": [{"id": "user-1", "email": "mouer@example.com", "name": "Marta"}],
        }

    async def get_items(self, model_name, skip=0, limit=10, filters=None, orders=None, populate=None):
        filters = filters or {}
        expected_id = filters.get("_id") or filters.get("id")
        items = [
            item for item in self.items.get(model_name, [])
            if expected_id is None or item.get("id") == expected_id
        ]
        return items[:limit], len(items)


class MatchWithNestedHook(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "postsave": [
                {
                    "lambda": "captureNested",
                    "to": "{{offerId.userId.email}}",
                    "context": {
                        "mouerName": "{{offerId.userId.name}}",
                    },
                }
            ]
        }
    })

    offerId: str


class MatchWithFlowConditions(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "postsave": [
                {
                    "lambda": "captureFlow",
                    "condition": "{{offerId}} != None",
                    "flow": "offer",
                },
                {
                    "lambda": "captureFlow",
                    "condition": "{{requestId}} != None",
                    "flow": "demand",
                },
            ]
        }
    })

    offerId: str | None = None
    requestId: str | None = None


@pytest.mark.asyncio
async def test_hook_resolves_nested_references_across_models():
    captured = {}

    async def capture_nested(**kwargs):
        captured.update(kwargs)

    register_lambda("captureNested", capture_nested)

    await execute_hooks(
        "postsave",
        MatchWithNestedHook,
        {"offerId": "offer-1"},
        repository=FakeRepository(),
    )

    assert captured["to"] == "mouer@example.com"
    assert captured["context"]["mouerName"] == "Marta"


@pytest.mark.asyncio
async def test_hook_conditions_can_split_offer_and_demand_match_flows():
    captured = []

    async def capture_flow(**kwargs):
        captured.append(kwargs["flow"])

    register_lambda("captureFlow", capture_flow)

    await execute_hooks(
        "postsave",
        MatchWithFlowConditions,
        {"offerId": "offer-1", "requestId": None},
        repository=FakeRepository(),
    )

    assert captured == ["offer"]
