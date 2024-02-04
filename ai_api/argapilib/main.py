from fastapi import FastAPI, HTTPException, status
from fastapi.routing import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .crud import CRUD
from typing import TypeVar
from .logger import _logger
from .Model import Model

T = TypeVar('T', bound='Model')

class FastApiARG():

    def __init__(self, db, crud: CRUD):
        self.db = db
        self.crud_instance = crud(db)
        self.api = FastAPI()
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def CRUD(self, model: T):
        model_name = model.__name__.lower()
        router = APIRouter(tags=[model.__name__])

        @router.post(f"/{model_name}/", response_model=dict)
        async def create_element(element: model):
            user_roles=["admin"]
            try:
                return await model.create(dict(element), model, user_roles, self.crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @router.put(f"/{model_name}"+"/{element_id}", response_model=dict)
        async def update_element(element_id: str, values: dict):
            user_roles=["admin"]
            try:
                return await model.update(element_id, values, model, user_roles, self.crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
        @router.get(f"/{model_name}"+"/{element_id}", response_model=dict)
        async def read_element(element_id: str):
            user_roles=["admin"]
            try:
                return await model.read(element_id, model, user_roles, self.crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @router.delete(f"/{model_name}"+"/{element_id}", response_model=str)
        async def delete_element(element_id: str):
            user_roles=["admin"]
            try:
                await model.delete(element_id, model, user_roles, self.crud_instance)
                return f"{model_name} element deleted successfully"
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


        self.api.include_router(router)