from typing import Type, List, Dict, Any
from pydantic import BaseModel
from math import ceil
from ..utils.utils import create_element
from ..crud.crud import CRUD
from .AccessRights import AccessRights
from ..utils.logger import _logger

class LaiaBaseModel(BaseModel):
    id: str = ""
    name: str

    @classmethod
    async def create(cls, new_element: dict, model: Type, user_roles: list, crud_instance: CRUD):
        _logger.info(f"Creating new {model.__name__} with values: {new_element}")

        try:
            element = model(**new_element)
        except Exception:
            raise ValueError("Missing required parameters")
    
        if "admin" not in user_roles:
            model_name = model.__name__.lower()
            access_rights_list = await cls.check_access_rights(model_name, user_roles, "create", crud_instance)
            await cls.check_fields_permission(model, 'fields_create', new_element, access_rights_list)
        
        created_element = await create_element(element, crud_instance)

        if "admin" not in user_roles:
            allowed_fields = cls.get_allowed_fields(access_rights_list, 'fields_visible')
            created_element = {field: created_element[field] for field in allowed_fields if field in created_element}

        _logger.info(f"{model.__name__} created successfully")
        return created_element
    
    @classmethod
    async def update(cls, element_id:str, updated_values: dict, model: Type, user_roles: list, crud_instance: CRUD):
        _logger.info(f"Updating {model.__name__} with ID: {element_id} and values: {updated_values}")

        model_name = model.__name__.lower()

        if "admin" not in user_roles:
            access_rights_list = await cls.check_access_rights(model_name, user_roles, "update", crud_instance)
            await cls.check_fields_permission(model, 'fields_edit', updated_values, access_rights_list)

        try:
            updated_element = await crud_instance.put_item(model_name, element_id, updated_values)
        except Exception:
            raise ValueError(f"{model.__name__} with ID does not exist, or the updating parameters have errors")
        
        if "admin" not in user_roles:
            allowed_fields = cls.get_allowed_fields(access_rights_list, 'fields_visible')
            updated_element = {field: updated_element[field] for field in allowed_fields if field in updated_element}

        _logger.info(f"{model.__name__} updated successfully")
        return updated_element
    
    @classmethod
    async def delete(cls, element_id: str, model: Type, user_roles: List[str], crud_instance: CRUD):
        _logger.info(f"Deleting {model.__name__} with ID: {element_id}")

        model_name = model.__name__.lower()

        if "admin" not in user_roles:
            await cls.check_access_rights(model_name, user_roles, "delete", crud_instance)
        try:
            await crud_instance.delete_item(model_name, element_id)
        except Exception:
            raise ValueError(f"{model.__name__} with ID does not exist, or there was an error deleting the element")

        _logger.info(f"{model.__name__} deleted successfully")

    @classmethod
    async def read(cls, element_id: str, model: Type, user_roles: List[str], crud_instance: CRUD):
        _logger.info(f"Getting {model.__name__} with ID: {element_id}")

        model_name = model.__name__.lower()

        if "admin" not in user_roles:
            access_rights_list = await cls.check_access_rights(model_name, user_roles, "read", crud_instance)
        try:
            item = await crud_instance.get_item(model_name, element_id)
        except ValueError as e:
            raise ValueError(str(e))

        if "admin" not in user_roles:
            allowed_fields = cls.get_allowed_fields(access_rights_list, 'fields_visible')
            item = {field: item[field] for field in allowed_fields if field in item}

        _logger.info(f"{model.__name__} retrieved successfully")
        return item
    
    @classmethod
    async def search(cls, skip: int, limit: int, filters: dict, orders: dict, model: Type, user_roles: List[str], crud_instance: CRUD):
        _logger.info(f"Searching {model.__name__} with filters: {filters}")

        model_name = model.__name__.lower()

        if "admin" not in user_roles:
            await cls.check_access_rights(model_name, user_roles, "search", crud_instance)

        try:
            items, total_count = await crud_instance.get_items(model_name, skip=skip, limit=limit, filters=filters, orders=orders)
            max_pages = ceil(total_count / limit)
            current_page = (skip // limit) + 1
        except Exception:
            raise ValueError(f"Error occurred while searching {model.__name__} with filters: {filters}")

        _logger.info(f"{model.__name__} search completed successfully")
        return {
            "items": items,
            "current_page": current_page,
            "max_pages": max_pages,
        }
    
    @classmethod
    async def check_access_rights(cls, model_name: str, roles: List[str], operation: str, crud_instance: CRUD):
        access_rights_list = []
        
        for role in roles:
            access_rights, _ = await crud_instance.get_items(
                "accessrights", 
                skip=0, 
                limit=1, 
                filters={
                    "model": model_name,
                    "role": role
                }
            )

            if access_rights and access_rights[0]["operations"].get(operation, 0) >= 1:
                access_rights_list.append(access_rights[0])

        if not access_rights_list:
            raise PermissionError(f"None of the roles have sufficient permissions for operation '{operation}' on model '{model_name}'")

        return access_rights_list
    
    @classmethod
    async def check_fields_permission(cls, model, fields_type: str, new_element: Dict[str, int], access_rights_list: List[AccessRights]):
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
                if access_rights.get(fields_type).get(field_name, {}) == 1:
                    allowed_by_some_role = True
                    break  

            if not allowed_by_some_role:
                raise PermissionError(f"Insufficient permissions to create the field '{field_name}' in any role.")

    @classmethod
    def get_allowed_fields(cls, access_rights_list: List[AccessRights], fields_type: str):
        allowed_fields = set()

        for access_rights in access_rights_list:
            fields = access_rights.get(fields_type, {})
            for field_name, field_value in fields.items():
                if field_value == 1:
                    allowed_fields.add(field_name)

        return allowed_fields
