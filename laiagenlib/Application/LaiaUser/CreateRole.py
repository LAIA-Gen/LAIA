from ...Application.Audit import write_audit_log
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.Role import Role
from ...Domain.Shared.Utils.logger import _logger


async def create_role(new_role: dict, user_roles: list, repository: ModelRepository, audit_context: dict = None, user_id: str = ""):
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
    await write_audit_log(
        repository,
        "CREATE",
        "Role",
        resource_id=created_role.get("id") or created_role.get("_id"),
        user_id=user_id,
        request_context=audit_context,
        before=None,
        after=created_role,
        status_code=200,
        success=True,
    )
    _logger.info("Role created successfully")
    return Role(**created_role)