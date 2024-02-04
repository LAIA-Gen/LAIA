from argapilib.main import FastApiARG
from argapilib.crud_mongo_impl import CRUDMongoImpl
from argapilib.Model import Model
from database import db
from fastapi.routing import APIRouter

# Inside app, we got: api (fastAPI), db (MongoClient), crud_instance (CRUDMongoImpl)
app_instance = FastApiARG(db, CRUDMongoImpl)

app = app_instance.api

# Define the models. Extending from the Model, which has 'id' and 'name'
class User(Model):
    description: str

class Drone(Model):
    description: str
    user_id: str
    model: str
    weight: float
    max_altitude: float
    max_speed: float

# Create CRUD routes to our FastAPI
app_instance.CRUD(User)
app_instance.CRUD(Drone)

# How can we add new custom routes to our API
router = APIRouter(tags=["Custom"])

@router.post("/custom_route/", response_model=dict)
async def create_item():
    pass

app.include_router(router)