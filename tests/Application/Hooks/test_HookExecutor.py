import pytest
from pydantic import ConfigDict

from laiagenlib.Application.Hooks.HookExecutor import execute_hooks
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


class FileScriptHook(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "postUpdate": [
                {
                    "script": "offer/update_offer_status",
                    "params": {
                        "source": "{{offerId.userId.email}}",
                    },
                }
            ]
        }
    })

    offerId: str
    statusOffer: str = "active"
    sourceEmail: str | None = None


class EscapingScriptHook(LaiaBaseModel):
    model_config = ConfigDict(json_schema_extra={
        "x-hooks": {
            "postupdate": [
                {"script": "../outside"}
            ]
        }
    })

    offerId: str


@pytest.mark.asyncio
async def test_hook_executes_python_script_file_and_resolves_params(tmp_path):
    hooks_dir = tmp_path / "hooks"
    script_dir = hooks_dir / "offer"
    script_dir.mkdir(parents=True)
    (script_dir / "update_offer_status.py").write_text(
        "\n".join([
            "async def run(context):",
            "    return {",
            "        'statusOffer': 'full',",
            "        'sourceEmail': context['params']['source'],",
            "    }",
        ]),
        encoding="utf-8",
    )

    element = await execute_hooks(
        "postupdate",
        FileScriptHook,
        {"offerId": "offer-1", "statusOffer": "active"},
        smtp_config={"hooks_dir": str(hooks_dir)},
        repository=FakeRepository(),
    )

    assert element["statusOffer"] == "full"
    assert element["sourceEmail"] == "mouer@example.com"


@pytest.mark.asyncio
async def test_hook_rejects_scripts_outside_hooks_directory(tmp_path):
    with pytest.raises(ValueError, match="escapes hooks directory"):
        await execute_hooks(
            "postupdate",
            EscapingScriptHook,
            {"offerId": "offer-1"},
            smtp_config={"hooks_dir": str(tmp_path / "hooks")},
            repository=FakeRepository(),
        )
