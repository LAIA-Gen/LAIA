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
                    "command": "captureNested",
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
                    "command": "captureFlow",
                    "condition": "{{offerId}} != None",
                    "flow": "offer",
                },
                {
                    "command": "captureFlow",
                    "condition": "{{requestId}} != None",
                    "flow": "demand",
                },
            ]
        }
    })

    offerId: str | None = None
    requestId: str | None = None


class TopLevelScriptHook(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "postupdate": [
                {
                    "script": None,
                    "condition": "true",
                    "execute": "totalSeatsOccupied = len(acceptedUserIds)",
                }
            ]
        }
    })

    acceptedUserIds: list = []
    totalSeatsOccupied: int = 0


class FileScriptHook(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "postupdate": [
                {
                    "script": "offer/update_offer_status",
                    "params": {
                        "source": "{{name}}",
                    },
                }
            ]
        }
    })

    name: str
    statusOffer: str = "active"
    sourceName: str | None = None


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


@pytest.mark.asyncio
async def test_hook_accepts_script_marker_with_top_level_execute():
    element = await execute_hooks(
        "postupdate",
        TopLevelScriptHook,
        {"acceptedUserIds": ["user-1", "user-2"], "totalSeatsOccupied": 0},
        repository=FakeRepository(),
    )

    assert element["totalSeatsOccupied"] == 2


@pytest.mark.asyncio
async def test_hook_executes_python_script_file(tmp_path):
    hooks_dir = tmp_path / "hooks"
    script_dir = hooks_dir / "offer"
    script_dir.mkdir(parents=True)
    (script_dir / "update_offer_status.py").write_text(
        "\n".join([
            "async def run(context):",
            "    return {",
            "        'statusOffer': 'full',",
            "        'sourceName': context['params']['source'],",
            "    }",
        ]),
        encoding="utf-8",
    )

    element = await execute_hooks(
        "postupdate",
        FileScriptHook,
        {"name": "Oferta test", "statusOffer": "active"},
        smtp_config={"hooks_dir": str(hooks_dir)},
        repository=FakeRepository(),
    )

    assert element["statusOffer"] == "full"
    assert element["sourceName"] == "Oferta test"
