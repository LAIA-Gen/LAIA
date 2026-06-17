import json

import pytest
from fastapi.testclient import TestClient

from laiagenlib.Application.LaiaUser.JWTToken import create_jwt_token
from laiagenlib.Infrastructure.Openapi.LaiaFastApi import LaiaFastApi


OPENAPI_CONTENT = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
components:
  schemas:
    Activity:
      type: object
      required:
        - name
      properties:
        name:
          type: string
"""


class StubRepository:
    def __init__(self, db):
        self.db = db

    async def get_items(self, model_name, skip=0, limit=10, filters={}, orders={}):
        return [], 0

    async def get_item(self, model_name, item_id):
        if model_name == "role" and item_id == "admin-role-id":
            return {"id": item_id, "name": "admin"}
        return None


class StubOpenapiRepository:
    def __init__(self, api, jwtSecretKey):
        self.api = api
        self.jwtSecretKey = jwtSecretKey

    async def create_roles_routes(self, repository=None, auth_required=False, jwtSecretKey="secret_key"):
        return None

    async def create_routes(self, repository=None, model=None, routes_info=None, jwtSecretKey="secret_key", auth_required=False):
        @self.api.post(**routes_info["create"], response_model=dict)
        async def create_element(element: model):
            return {}

    async def create_auth_user_routes(self, repository=None, model=None, routes_info=None, jwtSecretKey="secret_key", auth_required=False):
        return await self.create_routes(repository, model, routes_info, jwtSecretKey, auth_required)

    async def create_access_rights_routes(self, models=None, repository=None, auth_required=False, jwtSecretKey="secret_key"):
        return None


def stub_create_models_file(input_file, output_file, models, excluded_models):
    with open(output_file, "w", encoding="utf-8") as models_file:
        models_file.write(
            "from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel\n\n"
            "class Activity(LaiaBaseModel):\n"
            "    name: str\n"
        )


@pytest.fixture
def openapi_path(tmp_path):
    path = tmp_path / "openapi.yaml"
    path.write_text(OPENAPI_CONTENT, encoding="utf-8")
    (tmp_path / "laia.json").write_text(json.dumps({"version": "2.3.4"}), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_openapi_docs_use_laia_json_version_and_specific_resource_summary(openapi_path, monkeypatch):
    monkeypatch.setattr(
        "laiagenlib.Infrastructure.Openapi.LaiaFastApi.create_models_file",
        stub_create_models_file,
    )

    app_instance = await LaiaFastApi(
        str(openapi_path),
        "backend",
        object(),
        StubRepository,
        StubOpenapiRepository,
        "jwt-secret",
    )

    client = TestClient(app_instance.api)
    openapi = client.get("/openapi.json").json()

    assert openapi["info"]["version"] == "2.3.4"
    assert openapi["paths"]["/activity/"]["post"]["summary"] == "Create Activity"
    assert openapi["paths"]["/activity/"]["post"]["description"] == "Create a new Activity element."


@pytest.mark.asyncio
async def test_send_email_requires_admin_token(openapi_path, monkeypatch):
    monkeypatch.setattr(
        "laiagenlib.Infrastructure.Openapi.LaiaFastApi.create_models_file",
        stub_create_models_file,
    )

    app_instance = await LaiaFastApi(
        str(openapi_path),
        "backend",
        object(),
        StubRepository,
        StubOpenapiRepository,
        "jwt-secret",
    )

    @app_instance.api.post("/send-email/")
    async def send_email():
        return {"ok": True}

    client = TestClient(app_instance.api)
    user_token = create_jwt_token("user-id", "User", ["user"], "jwt-secret")
    admin_token = create_jwt_token("admin-id", "Admin", ["admin-role-id"], "jwt-secret")

    assert client.post("/send-email/").status_code == 401
    assert client.post("/send-email/", headers={"Authorization": f"Bearer {user_token}"}).status_code == 403
    assert client.post("/send-email/", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
