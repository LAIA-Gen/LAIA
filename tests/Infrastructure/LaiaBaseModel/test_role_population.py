"""Real MongoDB regression tests; each test owns a unique disposable database."""
import os
import uuid

import pytest
from bson import ObjectId
from pymongo import MongoClient

from laiagenlib.Infrastructure.LaiaBaseModel.MongoModelRepository import MongoModelRepository


@pytest.fixture
def role_db():
    client = MongoClient(os.environ.get('LAIA_TEST_MONGO_URI', 'mongodb://localhost:27017'), serverSelectionTimeoutMS=5000)
    name = 'laia_role_population_test_' + uuid.uuid4().hex
    database = client[name]
    try:
        yield database
    finally:
        assert database.name == name and name.startswith('laia_role_population_test_')
        client.drop_database(name)
        client.close()


POPULATE = [{'id': 'roles', 'from': 'Role', 'fields': ['name']}]


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_names_ids_missing_role_documents_and_nulls(role_db):
    seeker = role_db.role.insert_one({'name': 'seeker'}).inserted_id
    role_db.user.insert_many([
        {'name': 'name', 'roles': ['seeker']},
        {'name': 'id', 'roles': [str(seeker)]},
        {'name': 'objectid', 'roles': [seeker]},
        {'name': 'legacy', 'roles': ['mouer']},
        {'name': 'empty', 'roles': []},
        {'name': 'null', 'roles': None},
        {'name': 'absent'},
        {'name': 'dangling', 'roles': [str(ObjectId())]},
        {'name': 'mixed', 'roles': [str(seeker), 'mouer', '', None]},
    ])
    before = list(role_db.user.find())
    items, count = await MongoModelRepository(role_db).get_items('user', populate=POPULATE)
    assert count == 9
    by_name = {u['name']: u for u in items}
    for name in ['name', 'id', 'objectid']:
        assert by_name[name]['roles'][0]['name'] == 'seeker'
    assert by_name['legacy']['roles'][0]['name'] == 'mouer'
    assert by_name['legacy']['roles'][0]['_id'] == 'mouer'
    assert by_name['empty']['roles'] == []
    assert by_name['dangling']['roles'] == []
    assert {r['name'] for r in by_name['mixed']['roles']} == {'seeker', 'mouer'}
    assert list(role_db.user.find()) == before


@pytest.mark.anyio
@pytest.mark.parametrize('direction', [1, -1])
async def test_global_role_sort_and_filtered_page_counts(role_db, direction):
    seeker = role_db.role.insert_one({'name': 'seeker'}).inserted_id
    role_db.user.insert_many([
        {'name': 'A', 'roles': ['seeker']},
        {'name': 'B', 'roles': [str(seeker)]},
        {'name': 'C', 'roles': ['seeker', 'mouer']},
        {'name': 'D', 'roles': ['mouer']},
        {'name': 'E', 'roles': []},
    ])
    repo = MongoModelRepository(role_db)
    filters = {'roles.name': {'$regex': 'seek', '$options': 'i'}}
    orders = {'roles.name': direction, '_id': 1}
    all_items, count = await repo.get_items('user', limit=20, filters=filters, orders=orders, populate=POPULATE)
    assert count == 3
    # MongoDB sorts arrays by the smallest value ascending and largest descending.
    assert [u['name'] for u in all_items] == (['C', 'A', 'B'] if direction == 1 else ['A', 'B', 'C'])
    pages = []
    for offset in [0, 1, 2]:
        items, total = await repo.get_items('user', skip=offset, limit=1, filters=filters, orders=orders, populate=POPULATE)
        assert total == 3
        pages.extend(items)
    assert [u['id'] for u in pages] == [u['id'] for u in all_items]
    assert len({u['id'] for u in pages}) == 3
    assert all(any(r['name'] == 'seeker' for r in u['roles']) for u in pages)
    fallback, total = await repo.get_items('user', filters={'roles.name': 'mouer'}, populate=POPULATE)
    assert total == 2
    assert {u['name'] for u in fallback} == {'C', 'D'}


@pytest.mark.anyio
async def test_other_relations_still_resolve_only_ids(role_db):
    vehicle = role_db.vehicle.insert_one({'name': 'car'}).inserted_id
    role_db.user.insert_many([
        {'name': 'valid', 'vehicleId': [str(vehicle)]},
        {'name': 'invalid', 'vehicleId': ['car']},
    ])
    items, count = await MongoModelRepository(role_db).get_items('user', populate=[{'id': 'vehicleId', 'from': 'Vehicle'}])
    assert count == 2
    by_name = {u['name']: u for u in items}
    assert by_name['valid']['vehicleId'][0]['name'] == 'car'
    assert by_name['invalid']['vehicleId'] == []
