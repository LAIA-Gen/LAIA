from typing import List
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.Shared.Utils.logger import _logger

def get_allowed_fields(access_rights_list: List[AccessRight], fields_type: str):
    allowed_fields = set()

    for access_rights in access_rights_list:
        fields = getattr(access_rights, fields_type, {})
        for field_name, field_value in fields.items():
            if field_value == 1:
                allowed_fields.add(field_name)
        allowed_fields.add('id')

    return allowed_fields
