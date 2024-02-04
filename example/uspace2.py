from fastapi import FastAPI, HTTPException, status
from typing import List, Union, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from math import ceil
from argapilib.Model import Model
from argapilib.AccessRights import AccessRights
from argapilib.crud_mongo_impl import CRUDMongoImpl
from database import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

crud_instance = CRUDMongoImpl(db)

class User(Model):
    email: EmailStr

class Drone(Model):
    user_id: str
    model: str
    weight: float
    max_altitude: float
    max_speed: float

class Waypoint(Model):
    description: str
    coordinates: dict

    def validate_coordinates(cls, v):
        if v['type'] != 'Point' or len(v['coordinates']) != 2:
            raise ValueError('Coordinates must be a GeoJSON Point')
        return v

class FlightPlan(Model):
    drone_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    route: List[str]

class FlightPlanRoute(Model):
    drone_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    route: List[dict]

# User Routes

@app.post("/users/", response_model=dict)
async def create_user(user: User):
    user_roles=["admin"]
    try:
        return await User.create(user, User, user_roles, crud_instance)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/users/{user_id}", response_model=dict)
async def get_user(user_id: str):
    user_roles=["admin"]
    try:
        return await CRUDMongoImpl.get_item("users", user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

@app.post("/users/all", response_model=dict)
async def get_users(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
    try:
        items, total_count = await CRUDMongoImpl.get_items("users", skip=skip, limit=limit, filters=filters, orders=orders)

        max_pages = ceil(total_count / limit)
        current_page = (skip // limit) + 1

        return {
            "items": items,
            "current_page": current_page,
            "max_pages": max_pages,
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.put("/users/{user_id}", response_model=dict)
async def update_user(user_id: str, user: dict):
    user_role=["admin"]
    try:
        print(user)
        return await crud_instance.put_item(model_name="user", item_id=user_id, update_fields=user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.delete("/users/{user_id}", response_model=dict)
async def delete_user(user_id: str):
    try:
        return await CRUDMongoImpl.delete_item("users", user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in deleting the User")
