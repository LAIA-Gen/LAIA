from fastapi import FastAPI, Depends, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Mock authentication
class AuthenticatedUser:
    def __init__(self, role):
        self.role = role

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["your_database_name"]

# Pydantic models
class User(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "secure_password",
                "role": "user",
            }
        }

class Pet(BaseModel):
    name: str
    description: str
    owner: str

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "name": "Fluffy",
                "description": "Cute pet",
                "owner": "John Doe",
            }
        }

# FastAPI dependency for authenticated user
def get_authenticated_user(role: str = Depends(AuthenticatedUser)):
    return role

# Permission checks for fields
def check_field_permission(user_role, allowed_roles, required_roles=None):
    if required_roles is None:
        required_roles = allowed_roles

    if user_role not in allowed_roles:
        return None

    return {field: 1 for field in required_roles}

# CRUD operations
@app.post("/users/", response_model=User)
def create_user(user: User, authenticated_user: AuthenticatedUser = Depends(get_authenticated_user)):
    # Check permissions for creating user
    field_permissions = check_field_permission(authenticated_user.role, ["admin"])
    if field_permissions is not None:
        # Your logic to create user in the database
        return user
    raise HTTPException(status_code=403, detail="Permission denied")

@app.get("/users/{user_id}", response_model=User)
def read_user(
    user_id: str,
    fields: List[str] = None,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
):
    # Check permissions for reading user
    field_permissions = check_field_permission(
        authenticated_user.role, ["admin", "user"], required_roles=fields
    )
    if field_permissions is not None:
        # Your logic to retrieve user from the database
        return {"name": "John Doe", "email": "john@example.com", "role": "user"}
    raise HTTPException(status_code=403, detail="Permission denied")

@app.post("/pets/", response_model=Pet)
def create_pet(pet: Pet, authenticated_user: AuthenticatedUser = Depends(get_authenticated_user)):
    # Check permissions for creating pet
    field_permissions = check_field_permission(authenticated_user.role, ["admin", "owner"])
    if field_permissions is not None:
        # Your logic to create pet in the database
        return pet
    raise HTTPException(status_code=403, detail="Permission denied")

@app.get("/pets/{pet_id}", response_model=Pet)
def read_pet(
    pet_id: str,
    fields: List[str] = None,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
):
    # Check permissions for reading pet
    field_permissions = check_field_permission(
        authenticated_user.role, ["public", "admin"], required_roles=fields
    )
    if field_permissions is not None:
        # Your logic to retrieve pet from the database
        return {"name": "Fluffy", "description": "Cute pet", "owner": "John Doe"}
    raise HTTPException(status_code=403, detail="Permission denied")