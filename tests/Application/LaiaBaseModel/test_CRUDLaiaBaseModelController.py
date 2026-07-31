import pytest

from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from laiagenlib.Domain.Openapi.RoutesInfo import get_routes_info
from laiagenlib.Framework.LaiaBaseModel.CRUDLaiaBaseModelController import (
    CRUDLaiaBaseModelController,
)
from laiagenlib.Framework.LaiaBaseModel import CRUDLaiaBaseModelController as controller_module


class Example(LaiaBaseModel):
    name: str


class ExampleUpdate(LaiaBaseModel):
    name: str | None = None


@pytest.mark.asyncio
async def test_delete_forwards_smtp_config(monkeypatch):
    smtp_config = {"hooks_dir": "/app/backend/hooks"}
    captured = {}

    async def fake_delete(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(
        controller_module.DeleteLaiaBaseModel,
        "delete_laia_base_model",
        fake_delete,
    )

    router = CRUDLaiaBaseModelController(
        repository=object(),
        model=Example,
        update_model=ExampleUpdate,
        routes_info=get_routes_info("example"),
        auth_required=False,
        smtp_config=smtp_config,
    )
    delete_route = next(
        route
        for route in router.routes
        if getattr(route, "methods", set()) == {"DELETE"}
    )

    response = await delete_route.endpoint("example-id", None)

    assert response == "example element deleted successfully"
    assert captured["kwargs"]["smtp_config"] is smtp_config
