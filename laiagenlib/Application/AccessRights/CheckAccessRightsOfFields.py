from typing import List, Dict, Type
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.Shared.Utils.logger import _logger

async def check_access_rights_of_fields(model: Type, fields_type: str, new_element: Dict[str, int], access_rights_list: List[AccessRight]):
    model_fields = []

    for class_in_hierarchy in model.mro():
        if hasattr(class_in_hierarchy, '__annotations__'):
            model_fields.extend([field for field in class_in_hierarchy.__annotations__ if not field.startswith("_")])

    for field_name, field_value in new_element.items():
        if field_name not in model_fields:
            raise ValueError(f"Invalid field {field_name}")
        
    for field_name, field_value in new_element.items():
        allowed_by_some_role = False  

        for access_rights in access_rights_list:
            if hasattr(access_rights, fields_type):
                fields_dict = getattr(access_rights, fields_type)
                _logger.info(fields_dict)
                
                if field_name in fields_dict:
                    if fields_dict[field_name] == 1:
                        allowed_by_some_role = True
                        break

        if not allowed_by_some_role:
            raise PermissionError(f"Insufficient permissions to create the field '{field_name}' in any role.")