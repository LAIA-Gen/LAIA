"""HTTP integration tests with real controllers and a disposable MongoDB database."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import json
import os
from uuid import uuid4

import bcrypt
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ConfigDict
from pymongo import MongoClient
import pytest
import yaml

from laiagenlib.Application.Audit.Config import AuditConfig
from laiagenlib.Application.LaiaUser.JWTToken import create_jwt_token
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from laiagenlib.Domain.LaiaUser.LaiaUser import LaiaUser
from laiagenlib.Domain.Openapi.Openapi import OpenAPI
from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson
from laiagenlib.Framework.LaiaBaseModel.CRUDLaiaBaseModelController import CRUDLaiaBaseModelController
from laiagenlib.Framework.LaiaUser.AuthController import AuthController
from laiagenlib.Framework.Shared.AuditMiddleware import AuditMiddleware
from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository

SECRET = 'only-used-by-isolated-audit-tests'
ACTOR = '65f1a2b3c45d6e7890123456'


class Match(LaiaBaseModel):
    status: str = 'pending'
    players_count: int = 3


class MatchUpdate(LaiaBaseModel):
    status: str | None = None
    players_count: int | None = None


class User(LaiaUser):
    name: str = 'Audit test'
    model_config = ConfigDict(json_schema_extra={
        'x-hooks': {'auth_login': [{'script': 'user/add_login_event'}]},
    })


@pytest.fixture
def repo():
    client = MongoClient(os.getenv('LAIA_TEST_MONGO_URI', 'mongodb://localhost:27017'), serverSelectionTimeoutMS=5000)
    name = 'laia_audit_integration_' + uuid4().hex
    repository = MongoModelRepository(client[name])
    try:
        yield repository
    finally:
        assert name.startswith('laia_audit_integration_') and repository.db.name == name
        client.drop_database(name)
        client.close()


def bearer(roles=None, token_type='token'):
    tokens = create_jwt_token(ACTOR, 'Test', roles or ['admin'], SECRET, SECRET, {})
    return {'Authorization': 'Bearer ' + tokens[token_type]}


def make_app(repo, config=None, hooks_dir=None):
    app = FastAPI()
    app.add_middleware(AuditMiddleware, api=app, repository=repo,
                       config=config or AuditConfig(True, True), jwt_secret=SECRET)
    routes = {name: {'path': path} for name, path in {
        'create': '/match/', 'update': '/match/{element_id}',
        'read': '/match/{element_id}', 'delete': '/match/{element_id}',
        'search': '/matches/', 'nice': '/nice/match/{nicename}',
        'aggregate': '/matches/aggregate',
    }.items()}
    app.include_router(CRUDLaiaBaseModelController(repo, Match, MatchUpdate, routes,
                       jwtSecretKey=SECRET, auth_required=True, use_access_rights=True))
    app.include_router(AuthController(repo, User, SECRET, SECRET,
                       smtp_config={'hooks_dir': str(hooks_dir or os.getenv('LAIA_LOGIN_HOOK_DIR') or Path(__file__).parent / 'hooks')},
                       auth_required=True))

    @app.get('/vehicle/', tags=['Vehicle'])
    async def vehicle():
        return {'ok': True}

    @app.get('/unexpected/', tags=['Match'])
    async def unexpected():
        raise RuntimeError('test exception')

    @app.get('/rejected/', tags=['Match'])
    async def rejected():
        raise HTTPException(403, 'test rejection')

    @app.get('/concurrent/{element_id}', tags=['Match'])
    async def concurrent(element_id: str):
        await asyncio.sleep(0.02)
        return {'id': element_id}

    @app.post('/body/', tags=['System'])
    async def body(payload: dict):
        return {'ok': True}

    # These handlers intentionally have no own permissions: the middleware must
    # protect audit resources even if a schema is misconfigured as public.
    for model, plural in [('AuditLog', 'auditlogs'), ('LoginEvent', 'loginevents')]:
        async def read_record():
            return {'ok': True}
        async def search_element():
            return {'ok': True}
        app.add_api_route('/' + plural + '/', search_element, methods=['POST'], tags=[model])
        app.add_api_route('/' + model.lower() + '/', read_record, methods=['GET', 'PUT', 'DELETE', 'POST'], tags=[model])
        app.add_api_route('/' + plural + '/aggregate', read_record, methods=['POST'], tags=[model], name='aggregate_records')
    return app


def logs(repo):
    return serialize_bson(list(repo.db.auditlog.find().sort('_id', 1)))


def test_crud_http_snapshots_and_one_record_per_request(repo):
    with TestClient(make_app(repo)) as client:
        response = client.post('/match/', json={'status': 'pending', 'players_count': 3}, headers=bearer())
        assert response.status_code == 200, response.text
        resource = response.json()['id']
        response = client.put('/match/' + resource + '?source=test', json={'status': 'accepted', 'players_count': 4},
                              headers={**bearer(), 'X-Request-ID': 'req_abc123', 'User-Agent': 'Audit test'})
        assert response.status_code == 200, response.text
        assert response.headers['x-request-id'] == 'req_abc123'
        assert client.get('/match/' + resource, headers=bearer()).status_code == 200
        assert client.post('/matches/', json={}, headers=bearer()).status_code == 200
        assert client.delete('/match/' + resource, headers=bearer()).status_code == 200
    entries = logs(repo)
    assert [e['action'] for e in entries] == ['CREATE', 'UPDATE', 'READ', 'SEARCH', 'DELETE']
    update = entries[1]
    assert update['user'] == {'id': ACTOR}
    assert 'userId' not in update
    assert update['resource_id'] == resource
    assert update['request']['params'] == {'element_id': resource}
    assert update['request']['query'] == {'source': 'test'}
    assert update['request']['payload'] == {'status': 'accepted', 'players_count': 4}
    assert update['changes']['before']['status'] == 'pending'
    assert update['changes']['after']['status'] == 'accepted'
    assert update['result'] == {'status_code': 200, 'success': True}
    assert update['metadata']['request_id'] == 'req_abc123'
    assert entries[-1]['changes']['before']['players_count'] == 4
    assert entries[-1]['changes']['after'] is None


def test_failures_and_previously_uninstrumented_routes(repo):
    with TestClient(make_app(repo), raise_server_exceptions=False) as client:
        assert client.post('/match/', json={}, headers={}).status_code == 401
        assert client.post('/match/', json={'players_count': 'wrong'}, headers=bearer()).status_code == 422
        assert client.get('/rejected/', headers=bearer()).status_code == 403
        assert client.get('/match/' + str(ObjectId()), headers=bearer()).status_code == 404
        assert client.get('/unexpected/').status_code == 500
        assert client.post('/matches/aggregate', json=[], headers=bearer()).status_code == 200
        assert client.get('/nice/match/missing', headers=bearer()).status_code == 404
        assert client.get('/missing/').status_code == 404
    entries = logs(repo)
    assert [e['result']['status_code'] for e in entries] == [401, 422, 403, 404, 500, 200, 404, 404]
    assert entries[5]['action'] == 'AGGREGATE'
    assert all(e['result']['success'] is (e['result']['status_code'] < 400) for e in entries)


@pytest.mark.parametrize('enabled,before,excluded,expected', [
    (False, True, (), 0), (True, False, (), 1), (True, True, (), 1),
    (True, True, ('vehicle',), 0),
])
def test_configuration_and_before_request(repo, enabled, before, excluded, expected):
    app = make_app(repo, AuditConfig(enabled, before, excluded))
    @app.get('/observe/', tags=['Vehicle'])
    async def observe():
        existing = logs(repo)
        assert len(existing) == (1 if expected and before else 0)
        if existing:
            assert existing[0]['metadata']['phase'] == 'started'
            assert existing[0]['result']['status_code'] is None
        return {}
    with TestClient(app) as client:
        assert client.get('/observe/').status_code == 200
    assert len(logs(repo)) == expected
    if expected:
        assert logs(repo)[0]['metadata']['phase'] == 'completed'


def test_redaction_correlation_and_request_isolation(repo):
    app = make_app(repo)
    with TestClient(app) as client:
        payload = {'Password': 'never-store-me', 'nested': [{'refresh_token': 'secret'}], 'value': 1}
        assert client.post('/body/?api_key=secret', json=payload).status_code == 200
        response = client.get('/auth/verify/user/sensitive-token')
        assert response.status_code != 200
        def call(number):
            return client.get('/concurrent/' + str(number), headers={'X-Request-ID': 'parallel-' + str(number)})
        with ThreadPoolExecutor(max_workers=4) as pool:
            assert all(r.status_code == 200 for r in pool.map(call, range(8)))
    entries = logs(repo)
    assert entries[0]['request']['payload']['Password'] == '***'
    assert entries[0]['request']['payload']['nested'][0]['refresh_token'] == '***'
    assert entries[0]['request']['query']['api_key'] == '***'
    assert 'sensitive-token' not in json.dumps(entries[1], default=str)
    for entry in entries[2:]:
        assert entry['metadata']['request_id'] == 'parallel-' + entry['resource_id']


@pytest.mark.parametrize('model,plural', [('auditlog', 'auditlogs'), ('loginevent', 'loginevents')])
def test_audit_resources_are_admin_read_only_even_when_audit_disabled(repo, model, plural):
    with TestClient(make_app(repo, AuditConfig(False))) as client:
        assert client.get('/' + model + '/').status_code == 401
        assert client.get('/' + model + '/', headers=bearer(['seeker'])).status_code == 403
        assert client.get('/' + model + '/', headers=bearer(token_type='refresh_token')).status_code == 401
        assert client.get('/' + model + '/', headers=bearer()).status_code == 200
        assert client.post('/' + plural + '/', json={}, headers=bearer()).status_code == 200
        for method in ['post', 'put', 'delete']:
            assert getattr(client, method)('/' + model + '/', headers=bearer()).status_code == 405
        assert client.post('/' + plural + '/aggregate', json=[{'$out': 'user'}], headers=bearer()).status_code == 405


def seed_login(repo):
    repo.db.user.insert_one({'_id': ObjectId(ACTOR), 'email': 'audit@example.invalid',
                            'password': bcrypt.hashpw(b'test-password', bcrypt.gensalt(rounds=4)),
                            'name': 'Audit test', 'roles': ['admin']})


def test_login_writes_event_with_actual_request_context(repo):
    seed_login(repo)
    with TestClient(make_app(repo)) as client:
        for _ in range(2):
            response = client.post('/auth/login/user/', json={'email': 'audit@example.invalid', 'password': 'test-password'},
                                   headers={'User-Agent': 'Login test'})
            assert response.status_code == 200, response.text
            assert response.json()['token']
        bad = client.post('/auth/login/user/', json={'email': 'audit@example.invalid', 'password': 'incorrect'})
        assert bad.status_code == 401
    events = list(repo.db.loginevent.find())
    assert len(events) == 2
    assert all(str(e['userId']) == ACTOR and e['ipAddress'] == 'testclient' and e['userAgent'] == 'Login test' and e['createdAt'] for e in events)
    assert len(logs(repo)) == 3
    assert [e['result']['success'] for e in logs(repo)] == [True, True, False]
    assert 'test-password' not in json.dumps(logs(repo), default=str)


def test_login_event_failure_returns_no_tokens(repo, monkeypatch):
    seed_login(repo)
    original = repo.post_item
    async def fail_event(model, value):
        if model == 'loginevent':
            raise RuntimeError('event storage failure')
        return await original(model, value)
    monkeypatch.setattr(repo, 'post_item', fail_event)
    with TestClient(make_app(repo)) as client:
        response = client.post('/auth/login/user/', json={'email': 'audit@example.invalid', 'password': 'test-password'})
    assert response.status_code == 503
    assert 'token' not in response.json() and 'refresh_token' not in response.json()
    assert logs(repo)[0]['result'] == {'status_code': 503, 'success': False}


def test_audit_storage_failure_blocks_before_mutation(repo, monkeypatch):
    async def fail(*args, **kwargs):
        raise RuntimeError('audit storage failure')
    monkeypatch.setattr(repo, 'post_item', fail)
    with TestClient(make_app(repo)) as client:
        response = client.post('/match/', json={}, headers=bearer())
    assert response.status_code == 503
    assert repo.db.match.count_documents({}) == 0


def test_openapi_config_is_validated_and_defaults_off(tmp_path):
    path = tmp_path / 'base.yaml'
    path.write_text('openapi: 3.1.0\npaths: {}\ncomponents: {schemas: {}}\n')
    assert OpenAPI(path).audit_config == AuditConfig()
    path.write_text(path.read_text() + 'middleware:\n  auditlog:\n    enabled: true\n    before_request: true\n    exclude_models: [Vehicle]\n')
    assert OpenAPI(path).audit_config == AuditConfig(True, True, ('vehicle',))
    for value in [{'enabled': 'false'}, {'before_request': 1}, {'exclude_models': 'vehicle'}]:
        with pytest.raises(ValueError):
            AuditConfig.from_openapi({'middleware': {'auditlog': value}})


def test_disabled_or_excluded_crud_does_not_bypass_config(repo):
    for config in [AuditConfig(False), AuditConfig(True, True, ('match',))]:
        with TestClient(make_app(repo, config)) as client:
            assert client.post('/match/', json={}, headers=bearer()).status_code == 200
    assert logs(repo) == []


def test_failed_update_keeps_before_snapshot(repo, monkeypatch):
    resource = str(repo.db.match.insert_one({'status': 'pending', 'players_count': 3}).inserted_id)
    original = repo.put_item
    async def fail_match(model, *args, **kwargs):
        if model == 'match':
            raise RuntimeError('mutation failed')
        return await original(model, *args, **kwargs)
    monkeypatch.setattr(repo, 'put_item', fail_match)
    with TestClient(make_app(repo)) as client:
        response = client.put('/match/' + resource, json={'status': 'accepted'}, headers=bearer())
    assert response.status_code == 500
    entry = logs(repo)[0]
    assert entry['changes']['before']['status'] == 'pending'
    assert entry['changes']['after'] is None
    assert entry['metadata']['request_id'] == response.headers['x-request-id']


def test_final_audit_failure_returns_503_and_retains_pending_record(repo, monkeypatch):
    original = repo.put_item
    async def fail_audit(model, *args, **kwargs):
        if model == 'auditlog':
            raise RuntimeError('audit completion failed')
        return await original(model, *args, **kwargs)
    monkeypatch.setattr(repo, 'put_item', fail_audit)
    with TestClient(make_app(repo)) as client:
        response = client.post('/match/', json={}, headers=bearer())
    assert response.status_code == 503
    assert repo.db.match.count_documents({}) == 1
    assert logs(repo)[0]['metadata']['phase'] == 'started'


def test_admin_role_id_and_missing_login_hook(repo, tmp_path):
    role_id = repo.db.role.insert_one({'name': 'admin'}).inserted_id
    seed_login(repo)
    with TestClient(make_app(repo, hooks_dir=tmp_path)) as client:
        assert client.get('/auditlog/', headers=bearer([str(role_id)])).status_code == 200
        response = client.post('/auth/login/user/', json={'email': 'audit@example.invalid', 'password': 'test-password'})
    assert response.status_code == 503
    assert repo.db.loginevent.count_documents({}) == 0


def test_aggregation_cannot_overwrite_audit_collections(repo):
    from laiagenlib.Application.LaiaBaseModel.AggregateLaiaBaseModel import protect_audit_collections
    for stage in [{'$lookup': {'from': 'auditlog'}}, {'$unionWith': {'coll': 'loginevent'}}]:
        with pytest.raises(PermissionError):
            protect_audit_collections([{'$facet': {'nested': [stage]}}], ['seeker'])
        protect_audit_collections([stage], ['admin'])
    with TestClient(make_app(repo)) as client:
        for stage in [{'$out': 'auditlog'}, {'$merge': {'into': {'db': repo.db.name, 'coll': 'loginevent'}}}]:
            assert client.post('/matches/aggregate', json=[stage], headers=bearer()).status_code == 403
    assert len(logs(repo)) == 2
    assert repo.db.loginevent.count_documents({}) == 0


def test_factory_installs_audit_and_preserves_configuration_in_export(repo, tmp_path):
    from laiagenlib.Infrastructure.Openapi.LaiaFastApi import LaiaFastApi
    from laiagenlib.Infrastructure.Openapi.FastAPIOpenapiRepository import FastAPIOpenapiRepository
    spec = {
        'openapi': '3.1.0', 'info': {'title': 'Audit integration', 'version': '1'}, 'paths': {},
        'middleware': {'auditlog': {'enabled': True, 'before_request': True, 'exclude_models': ['Vehicle']}},
        'components': {'schemas': {
            'AuditLog': {'type': 'object', 'permissions': {'read': ['admin'], 'search': ['admin']},
                         'properties': {'action': {'type': 'string'}, 'user': {'type': 'object', 'additionalProperties': True}}},
            'Vehicle': {'type': 'object', 'properties': {'name': {'type': 'string'}}},
        }},
    }
    source = tmp_path / 'openapi.yaml'
    source.write_text(yaml.safe_dump(spec))
    factory = asyncio.run(LaiaFastApi(str(source), 'generated', repo.db, MongoModelRepository,
                           FastAPIOpenapiRepository, False, False, jwtSecretKey=SECRET,
                           add_storage=False, add_geolocation=False))
    with TestClient(factory.api) as client:
        response = client.get('/openapi.json')
        assert response.status_code == 200
        exported = response.json()
        assert exported['middleware']['auditlog'] == AuditConfig(True, True, ('vehicle',)).as_dict()
        assert client.post('/auditlogs/', json={}).status_code == 401
        assert client.post('/auditlogs/', json={}, headers=bearer()).status_code == 200
        before = len(logs(repo))
        assert client.post('/vehicles/', json={}).status_code == 200
        assert len(logs(repo)) == before
    source.write_text(yaml.safe_dump(exported))
    assert OpenAPI(source).audit_config == AuditConfig(True, True, ('vehicle',))
