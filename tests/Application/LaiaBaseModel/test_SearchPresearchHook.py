from pydantic import ConfigDict
import pytest

from laiagenlib.Application.LaiaBaseModel.SearchLaiaBaseModel import (
    search_laia_base_model,
)
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel


class HookedOffer(LaiaBaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "x-hooks": {
                "presearch": [{"script": "offer/filter_non_admin"}],
            },
        },
    )


class CapturingRepository:
    def __init__(self):
        self.filters = None

    async def get_items(self, model_name, skip, limit, filters, orders, populate):
        self.filters = filters
        return [], 0


@pytest.mark.asyncio
async def test_presearch_receives_auth_context_and_mutates_filters(tmp_path):
    hook_dir = tmp_path / "hooks" / "offer"
    hook_dir.mkdir(parents=True)
    (hook_dir / "filter_non_admin.py").write_text(
        "async def run(context):\n"
        "    if 'admin' not in context['user_roles']:\n"
        "        context['element']['filteredFor'] = context['user_id']\n",
        encoding="utf-8",
    )
    repository = CapturingRepository()

    await search_laia_base_model(
        0,
        10,
        {},
        {},
        HookedOffer,
        ["user"],
        repository,
        user_id="user-id",
        use_access_rights=False,
        smtp_config={"hooks_dir": str(tmp_path / "hooks")},
    )

    assert repository.filters == {"filteredFor": "user-id"}
