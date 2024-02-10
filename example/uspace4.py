from laiagenlib.main import LaiaFastApi
from laiagenlib.crud.crud_mongo_impl import CRUDMongoImpl
from laiagenlib.utils.logger import _logger
from database import db
from fastapi.routing import APIRouter
import os

# Inside app, we got: api (fastAPI), db (MongoClient), crud_instance (CRUDMongoImpl)
models_path = os.path.join(os.getcwd(), "api2.yaml")
_logger.info(models_path)

app_instance = LaiaFastApi(models_path, db, CRUDMongoImpl)

app = app_instance.api
