import pytest
from pydantic import BaseModel
from unittest.mock import MagicMock
from laiagenlib.Application.AccessRights.CheckAccessRightsOfFields import check_access_rights_of_fields
from laiagenlib.Domain.AccessRights.AccessRights import AccessRight

class ExampleModel(BaseModel):
    field1: int
    field2: int

class TestCheckAccessRightsOfFields:
    @pytest.mark.asyncio
    async def test_valid_fields(self):

        access_rights_list = [
            AccessRight(role="admin", model="ExampleModel", fields_create={"field1": 1}),
            AccessRight(role="user", model="ExampleModel", fields_create={"field2": 1})
        ]
        new_element = {"field1": 123, "field2": 456}
        await check_access_rights_of_fields(ExampleModel, "fields_create", new_element, access_rights_list)

    @pytest.mark.asyncio
    async def test_invalid_field(self):

        access_rights_list = [
            AccessRight(role="admin", model="ExampleModel", fields_create={"field1": 1}),
            AccessRight(role="user", model="ExampleModel", fields_create={"field2": 1})
        ]

        new_element = {"field1": 123, "invalid_field": 456}
        with pytest.raises(ValueError):
            await check_access_rights_of_fields(ExampleModel, "fields_create", new_element, access_rights_list)

    @pytest.mark.asyncio
    async def test_insufficient_permissions(self):

        access_rights_list = [
            AccessRight(role="user", model="ExampleModel", fields_create={"field1": 0})
        ]

        new_element = {"field1": 123}
        with pytest.raises(PermissionError):
            await check_access_rights_of_fields(ExampleModel, "fields_create", new_element, access_rights_list)