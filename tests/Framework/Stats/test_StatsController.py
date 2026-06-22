import json

import pytest

from laiagenlib.Framework.Stats import StatsController


class StatsRepositoryStub:
    def __init__(self):
        self.aggregate_calls = 0
        self.model_names = []

    async def get_items(self, model_name, limit):
        self.model_names.append(model_name)
        return [], 3

    async def aggregate_items(self, model_name, pipeline):
        self.model_names.append(model_name)
        self.aggregate_calls += 1

        if self.aggregate_calls == 1:
            return [
                {"_id": "seeker", "count": 2},
                {"_id": "volunteer", "count": 1},
            ]
        if self.aggregate_calls == 2:
            return [{"count": 2}]
        return [{"count": 3}]


@pytest.mark.asyncio
async def test_users_stats_uses_openapi_user_model_name_as_collection():
    repository = StatsRepositoryStub()
    router = StatsController(repository, user_model="User")
    route = next(route for route in router.routes if route.path == "/stats/users")

    response = await route.endpoint()
    body = json.loads(response.body)

    assert repository.model_names == ["user", "user", "user", "user"]
    assert body == {
        "total_users": 3,
        "users_by_role": {"seeker": 2, "volunteer": 1},
        "active_users": {"daily": 2, "monthly": 3},
    }
