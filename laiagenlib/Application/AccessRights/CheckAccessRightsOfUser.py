from typing import List
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.Shared.Utils.logger import _logger

async def check_access_rights_of_user(model_name: str, roles: List[str], operation: str, repository: ModelRepository):
    access_rights_list = []
    
    for role_name in roles:
        role, _ = await repository.get_items(
            "role",
            skip = 0, 
            limit = 1, 
            filters={
                "name": role_name
            }
        )
        _logger.info(role)
        access_rights, _ = await repository.get_items(
            "accessright", 
            skip=0, 
            limit=1, 
            filters={
                "model": model_name,
                "role": role[0]['id']
            }
        )

        if access_rights and access_rights[0]["operations"].get(operation, 0) >= 1:
            access_rights_list.append(AccessRight(**access_rights[0]))

    if not access_rights_list:
        raise PermissionError(f"None of the roles have sufficient permissions for operation '{operation}' on model '{model_name}'")

    return access_rights_list