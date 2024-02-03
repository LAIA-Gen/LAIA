from fastapi import FastAPI, HTTPException, status
from typing import List
from pydantic import BaseModel, EmailStr
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
#from crud_mongo import CRUDMongoImpl
from bson import ObjectId
from math import ceil
from argapilib.models import Role, Model, AccessRights
from argapilib.crud_mongo_impl import CRUDMongoImpl
from database import db
import asyncio

class Usera(Model):
    description: str

app = FastAPI()

database_instance = CRUDMongoImpl(db)
async def start ():
    user = await Usera.create(Usera(name="alba", description="very well then"), ["admin"], database_instance)
    print(user)

async def main():
    await start()

# Run the event loop
if __name__ == "__main__":
    asyncio.run(main())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# use 'id' for identificator
class User(BaseModel):
    name: str
    email: EmailStr

class Drone(BaseModel):
    name: str
    user_id: str
    model: str
    weight: float
    max_altitude: float
    max_speed: float

class Waypoint(BaseModel):
    name: str
    description: str
    coordinates: dict  # GeoJSON Point

    def validate_coordinates(cls, v):
        if v['type'] != 'Point' or len(v['coordinates']) != 2:
            raise ValueError('Coordinates must be a GeoJSON Point')
        return v

class FlightPlan(BaseModel):
    name: str
    drone_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    route: List[str]

class FlightPlanRoute(BaseModel):
    name: str
    drone_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    route: List[dict]

# User Routes

@app.post("/users/", response_model=dict)
async def create_user(user: User):
    try:
        return await CRUDMongoImpl.post_item("users", user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in creating a User")

@app.get("/users/{user_id}", response_model=dict)
async def get_user(user_id: str):
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in getting the list of Users")

@app.put("/users/{user_id}", response_model=dict)
async def update_user(user_id: str, user: User):
    try:
        return await CRUDMongoImpl.put_item("users", user_id, user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in updating the User")

@app.delete("/users/{user_id}", response_model=dict)
async def delete_user(user_id: str):
    try:
        return await CRUDMongoImpl.delete_item("users", user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in deleting the User")

# Drone Routes

@app.post("/drones/", response_model=dict)
async def create_drone(drone: Drone):
    return await CRUDMongoImpl.post_item("drones", drone)

@app.get("/drones/{drone_id}", response_model=dict)
async def get_drone(drone_id: str):
    return await CRUDMongoImpl.get_item("drones", drone_id)

@app.post("/drones/all", response_model=dict)
async def get_drones(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
    print(f"Received request with skip={skip}, limit={limit}, filters={filters}, orders={orders}")

    items, total_count = await CRUDMongoImpl.get_items("drones", skip=skip, limit=limit, filters=filters, orders=orders)

    max_pages = ceil(total_count / limit)
    current_page = (skip // limit) + 1

    return {
        "items": items,
        "current_page": current_page,
        "max_pages": max_pages,
    }

@app.put("/drones/{drone_id}", response_model=dict)
async def update_drone(drone_id: str, drone: Drone):
    return await CRUDMongoImpl.put_item("drones", drone_id, drone)

@app.delete("/drones/{drone_id}", response_model=dict)
async def delete_drone(drone_id: str):
    return await CRUDMongoImpl.delete_item("drones", drone_id)

# FlightPlan Routes

@app.post("/flightplans/", response_model=dict)
async def create_flight_plan(flight_plan: FlightPlan):
    try:
        return await CRUDMongoImpl.post_item("flight_plans", flight_plan)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in creating a FlightPlan")

@app.get("/flightplans/{flight_plan_id}", response_model=dict)
async def get_flight_plan(flight_plan_id: str):
    return await CRUDMongoImpl.get_item("flight_plans", flight_plan_id)

@app.post("/flightplans/all", response_model=dict)
async def get_flight_plans(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
    items, total_count = await CRUDMongoImpl.get_items("flight_plans", skip=skip, limit=limit, filters=filters, orders=orders)

    max_pages = ceil(total_count / limit)
    current_page = (skip // limit) + 1

    return {
        "items": items,
        "current_page": current_page,
        "max_pages": max_pages,
    }

@app.put("/flightplans/{flight_plan_id}", response_model=dict)
async def update_flight_plan(flight_plan_id: str, flight_plan: dict):
    return await CRUDMongoImpl.put_item("flight_plans", flight_plan_id, flight_plan)

@app.delete("/flightplans/{flight_plan_id}", response_model=dict)
async def delete_flight_plan(flight_plan_id: str):
    return await CRUDMongoImpl.delete_item("flight_plans", flight_plan_id)

# Waypoint Routes

@app.post("/waypoints/", response_model=Waypoint)
async def create_waypoint(waypoint: Waypoint):
    return await CRUDMongoImpl.post_item("waypoints", waypoint)

@app.get("/waypoints/{waypoint_id}", response_model=dict)
async def get_waypoint(waypoint_id: str):
    return await CRUDMongoImpl.get_item("waypoints", waypoint_id)

@app.post("/waypoints/all", response_model=dict)
async def get_waypoints(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
    items, total_count = await CRUDMongoImpl.get_items("waypoints", skip=skip, limit=limit, filters=filters, orders=orders)

    max_pages = ceil(total_count / limit)
    current_page = (skip // limit) + 1

    return {
        "items": items,
        "current_page": current_page,
        "max_pages": max_pages,
    }


@app.put("/waypoints/{waypoint_id}", response_model=dict)
async def update_waypoint(waypoint_id: str, waypoint: Waypoint):
    return await CRUDMongoImpl.put_item("waypoints", waypoint_id, waypoint)

@app.delete("/waypoints/{waypoint_id}", response_model=dict)
async def delete_waypoint(waypoint_id: str):
    return await CRUDMongoImpl.delete_item("waypoints", waypoint_id)

@app.post("/flightplanroutes/", response_model=dict)
async def create_flightplanroutes(flightplanroutes: FlightPlanRoute):
    return await CRUDMongoImpl.post_item("flightplanroutes", flightplanroutes)

@app.get("/flightplanroutes/{flightplanroutes_id}", response_model=dict)
async def get_flightplanroutes(flightplanroutes_id: str):
    return await CRUDMongoImpl.get_item("flightplanroutes", flightplanroutes_id)

@app.post("/flightplanroutes/all", response_model=dict)
async def get_flightplanroutes(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
    items, total_count = await CRUDMongoImpl.get_items("flightplanroutes", skip=skip, limit=limit, filters=filters, orders=orders)

    max_pages = ceil(total_count / limit)
    current_page = (skip // limit) + 1

    return {
        "items": items,
        "current_page": current_page,
        "max_pages": max_pages,
    }


@app.put("/flightplanroutes/{flightplanroutes_id}", response_model=dict)
async def update_flightplanroutes(flightplanroutes_id: str, flightplanroutes: FlightPlanRoute):
    return await CRUDMongoImpl.put_item("flightplanroutes", flightplanroutes_id, flightplanroutes)

@app.delete("/flightplanroutes/{flightplanroutes_id}", response_model=dict)
async def delete_flightplanroutes(flightplanroutes_id: str):
    return await CRUDMongoImpl.delete_item("flightplanroutes", flightplanroutes_id)