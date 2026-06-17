import pytest

from laiagenlib.Infrastructure.Openapi.LaiaFastApi import LaiaFastApi


OPENAPI_CONTENT = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
components:
  schemas:
    Widget:
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


class StubOpenapiRepository:
    def __init__(self, api, jwtSecretKey):
        self.api = api
        self.jwtSecretKey = jwtSecretKey
        self.calls = []

    async def create_roles_routes(self, repository=None, auth_required=False, jwtSecretKey="secret_key"):
        self.calls.append(("roles", jwtSecretKey, auth_required))

    async def create_routes(self, repository=None, model=None, routes_info=None, jwtSecretKey="secret_key", auth_required=False):
        self.calls.append(("crud", model.__name__, jwtSecretKey, auth_required))

    async def create_auth_user_routes(self, repository=None, model=None, routes_info=None, jwtSecretKey="secret_key", auth_required=False):
        self.calls.append(("auth", model.__name__, jwtSecretKey, auth_required))

    async def create_access_rights_routes(self, models=None, repository=None, auth_required=False, jwtSecretKey="secret_key"):
        self.calls.append(("access_rights", sorted(models), jwtSecretKey, auth_required))


def stub_create_models_file(input_file, output_file, models, excluded_models):
    with open(output_file, "w", encoding="utf-8") as models_file:
        models_file.write(
            "from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel\n\n"
            "class Widget(LaiaBaseModel):\n"
            "    name: str\n"
        )


@pytest.fixture
def openapi_path(tmp_path):
    path = tmp_path / "openapi.yaml"
    path.write_text(OPENAPI_CONTENT, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_laia_fast_api_accepts_new_generated_backend_signature(openapi_path, monkeypatch):
    monkeypatch.setattr(
        "laiagenlib.Infrastructure.Openapi.LaiaFastApi.create_models_file",
        stub_create_models_file,
    )

    app = await LaiaFastApi(
        str(openapi_path),
        "backend",
        object(),
        StubRepository,
        StubOpenapiRepository,
        False,
        True,
        "jwt-secret",
        "refresh-secret",
        True,
        "minio:9000",
        "minio-user",
        "minio-password",
        "smtp.example.com",
        587,
        "smtp-user",
        "smtp-password",
        True,
        templates_dir=str(openapi_path.parent / "email_templates"),
    )

    assert app.jwtSecretKey == "jwt-secret"
    assert app.jwtRefreshSecretKey == "refresh-secret"
    assert app.use_ontology is False
    assert app.use_access_rights is True
    assert app.minio_endpoint_url == "minio:9000"
    assert app.smtp_host == "smtp.example.com"
    assert app.templates_dir.endswith("email_templates")
    assert ("access_rights", ["Widget"], "jwt-secret", False) in app.repository_api_instance.calls


@pytest.mark.asyncio
async def test_laia_fast_api_keeps_old_signature_compatibility(openapi_path, monkeypatch):
    monkeypatch.setattr(
        "laiagenlib.Infrastructure.Openapi.LaiaFastApi.create_models_file",
        stub_create_models_file,
    )

    app = await LaiaFastApi(
        str(openapi_path),
        "backend",
        object(),
        StubRepository,
        StubOpenapiRepository,
        "old-secret",
    )

    assert app.jwtSecretKey == "old-secret"
    assert app.jwtRefreshSecretKey is None
    assert app.use_ontology is False
    assert app.use_access_rights is True
    assert ("access_rights", ["Widget"], "old-secret", False) in app.repository_api_instance.calls
