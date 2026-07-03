from bson import ObjectId
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository

async def resolve_role_ids(roles: list, repository: ModelRepository) -> list:
    resolved_roles = []
    if not isinstance(roles, list):
        roles = [roles]
    for role in roles:
        if not isinstance(role, str):
            role = str(role)
        
       # Check if it is a valid 24-character ObjectID
        is_object_id = False
        if len(role) == 24:
            try:
                role_found, _ = await repository.get_items("role", filters={"id": ObjectId(role)})
                if role_found:
                    is_object_id = True 
            except Exception:
                raise ValueError(f"Role '{role}' not found")
         
        if is_object_id:
            resolved_roles.append(role)
        else:
            # Search by name in "role" collection
            roles_found, _ = await repository.get_items("role", filters={"name": role})
            if roles_found:
                resolved_roles.append(roles_found[0]['id'])
            else:
                raise ValueError(f"Role '{role}' not found")
    return resolved_roles
