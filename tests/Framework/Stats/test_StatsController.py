import json

import pytest
from bson import ObjectId

from laiagenlib.Framework.Stats import LaiaMetricsRegistry, StatsController


class RequestStub:
    def __init__(self, query_params):
        self.query_params = query_params


class CollectionStub:
    def __init__(self, count=0, aggregate_results=None):
        self.aggregate_calls = 0
        self.count = count
        self.last_filter = None
        self.last_pipeline = None
        self.aggregate_results = aggregate_results or []

    def count_documents(self, filters):
        self.last_filter = filters
        return self.count

    def aggregate(self, pipeline):
        self.aggregate_calls += 1
        self.last_pipeline = pipeline

        if self.aggregate_calls == 1:
            return [
                {"_id": "seeker", "count": 2},
                {"_id": "volunteer", "count": 1},
            ]
        if self.aggregate_calls == 2:
            return [{"count": 2}]
        if self.aggregate_calls == 3:
            return [{"count": 3}]

        return self.aggregate_results


class RepositoryStub:
    def __init__(self, collections):
        self.db = collections


@pytest.fixture(autouse=True)
def clear_metrics_registry():
    LaiaMetricsRegistry._registry.clear()
    yield
    LaiaMetricsRegistry._registry.clear()


@pytest.mark.asyncio
async def test_users_stats_uses_openapi_user_model_name_as_collection():
    user_collection = CollectionStub(count=3)
    repository = RepositoryStub({"user": user_collection})
    router = StatsController(repository, user_model="User")
    route = next(route for route in router.routes if route.path == "/stats/users")

    response = await route.endpoint()
    body = json.loads(response.body)

    assert user_collection.last_filter == {}
    assert user_collection.aggregate_calls == 3
    assert body == {
        "total_users": 3,
        "users_by_role": {"seeker": 2, "volunteer": 1},
        "active_users": {"daily": 2, "monthly": 3},
    }


@pytest.mark.asyncio
async def test_yaml_metric_accepts_activity_id_query_param(tmp_path):
    activity_id = ObjectId()
    metrics_file = tmp_path / "metrics.yaml"
    metrics_file.write_text(
        """
metrics:
  - name: offers_for_activity
    collection: offer
    type: count
    params:
      activityId:
        type: objectId
        required: true
    filters:
      activityId: "{{activityId}}"
""",
        encoding="utf-8",
    )

    offer_collection = CollectionStub(count=5)
    repository = RepositoryStub({"offer": offer_collection})
    router = StatsController(repository, user_model="User", metrics_file=str(metrics_file))
    route = next(route for route in router.routes if route.path == "/stats/custom/{metric_name}")

    response = await route.endpoint(
        "offers_for_activity",
        RequestStub({"activityId": str(activity_id)}),
    )
    body = json.loads(response.body)

    assert offer_collection.last_filter == {"activityId": activity_id}
    assert body == {"offers_for_activity": 5}


@pytest.mark.asyncio
async def test_by_activity_route_executes_metric_with_activity_id_box(tmp_path):
    activity_id = ObjectId()
    metrics_file = tmp_path / "metrics.yaml"
    metrics_file.write_text(
        """
metrics:
  - name: offers_for_activity
    collection: offer
    type: count
    params:
      activityId:
        type: objectId
        required: true
    filters:
      activityId: "{{activityId}}"
""",
        encoding="utf-8",
    )

    offer_collection = CollectionStub(count=7)
    repository = RepositoryStub({"offer": offer_collection})
    router = StatsController(repository, user_model="User", metrics_file=str(metrics_file))
    route = next(route for route in router.routes if route.path == "/stats/custom/{metric_name}/by-activity")

    response = await route.endpoint(
        metric_name="offers_for_activity",
        request=RequestStub({"activityId": str(activity_id)}),
        activityId=str(activity_id),
    )
    body = json.loads(response.body)

    assert offer_collection.last_filter == {"activityId": activity_id}
    assert body == {"offers_for_activity": 7}
