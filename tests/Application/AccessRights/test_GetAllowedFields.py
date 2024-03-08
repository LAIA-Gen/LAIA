import pytest
from laiagenlib.Domain.AccessRights.AccessRights import AccessRight
from laiagenlib.Application.AccessRights.GetAllowedFields import get_allowed_fields

@pytest.fixture
def access_rights_list():
    access_rights_1 = AccessRight(
        role="user",
        model="example",
        operations={"create": 1},
        fields_create={"field1": 1, "field2": 0}, 
        fields_edit={"field1": 1, "field3": 1},    
        fields_visible={"field2": 1}               
    )
    access_rights_2 = AccessRight(
        role="admin",
        model="example",
        operations={"create": 1},
        fields_create={"field3": 1},               
        fields_edit={"field1": 1},                  
        fields_visible={"field1": 0, "field2": 1}  
    )
    return [access_rights_1, access_rights_2]

def test_get_allowed_fields(access_rights_list):
    assert get_allowed_fields(access_rights_list, "fields_create") == {"field1", "field3"}

    assert get_allowed_fields(access_rights_list, "fields_edit") == {"field1", "field3"}

    assert get_allowed_fields(access_rights_list, "fields_visible") == {"field2"}
