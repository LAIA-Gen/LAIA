import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from bson import ObjectId
from test_audit_login import repo, SECRET, logs
from laiagenlib.Framework.LaiaUser.CRUDRoleController import CRUDRoleController
from laiagenlib.Framework.Shared.AuditMiddleware import AuditMiddleware
from laiagenlib.Application.Audit.Config import AuditConfig
from laiagenlib.Application.LaiaUser.JWTToken import create_jwt_token


def test_internal_role_reads_do_not_pollute_request_audit(repo):
    app = FastAPI()
    app.add_middleware(AuditMiddleware, api=app, repository=repo,
                       config=AuditConfig(True, True), jwt_secret=SECRET)
    app.include_router(asyncio.run(CRUDRoleController(repo, SECRET, True)))
    admin = repo.db.role.find_one({'name': 'admin'})
    actor = str(ObjectId())
    token = create_jwt_token(actor, 'Audit regression', [str(admin['_id'])], SECRET, SECRET, {})['token']
    headers = {'Authorization': 'Bearer ' + token}
    with TestClient(app) as client:
        response = client.post('/role/', json={'name': 'Audit temporary role'}, headers=headers)
        assert response.status_code == 200
        resource = response.json()['id']
        assert client.put('/role/' + resource, json={'name': 'Updated role'}, headers=headers).status_code == 200
        assert client.get('/role/' + resource, headers=headers).status_code == 200
        assert client.delete('/role/' + resource, headers=headers).status_code == 200
        assert client.get('/role/' + resource, headers=headers).status_code == 404
    entries = logs(repo)
    assert len(entries) == 5
    assert [entry['action'] for entry in entries] == ['CREATE', 'UPDATE', 'READ', 'DELETE', 'READ']
    assert all(entry['user']['id'] == actor and entry['resource_id'] == resource for entry in entries)
    assert entries[0]['changes']['after']['name'] == 'Audit temporary role'
    assert entries[1]['changes']['before']['name'] == 'Audit temporary role'
    assert entries[1]['changes']['after']['name'] == 'Updated role'
    assert entries[2]['changes']['after']['name'] == 'Updated role'
    assert entries[3]['changes']['before']['name'] == 'Updated role'
    assert entries[4]['changes'] == {'before': None, 'after': None}
