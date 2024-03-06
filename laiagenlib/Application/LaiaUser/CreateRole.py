from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.Role import Role
from ...Domain.Shared.Utils.logger import _logger

async def create_role(new_role: dict, user_roles: list, repository: ModelRepository):
    _logger.info(f"Creating new Role with values: {new_role}")

    if "name" not in new_role:
        raise ValueError("Missing required parameter: name")

    role = Role(**new_role)
    if "admin" not in user_roles:
        raise PermissionError("Only users with 'admin' role can create new roles")

    existing_roles, _ = await repository.get_items("role", skip=0, limit=10, filters={"name": role.name})
    if existing_roles:
        raise ValueError(f"Role with name '{role.name}' already exists")
    
    created_role = await repository.post_item(
        "role",
        role.model_dump()
    )
    _logger.info("Role created successfully")
    return Role(**created_role)
