from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
from typing import TypeVar, Type

from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from .MetricsRegistry import LaiaMetricsRegistry
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def StatsController(repository: ModelRepository, user_model: Type[T] = None):
    router = APIRouter(tags=["Stats"])

    @router.get("/stats/users")
    async def get_users_stats():
        if not user_model:
            raise HTTPException(status_code=500, detail="user_model not configured for StatsController")
        
        try:
            model_name = user_model.__name__.lower()
            
            # Total users
            _, total_users = await repository.get_items(model_name=model_name, limit=0)

            # Users by role
            role_pipeline = [
                { "$unwind": { "path": "$roles", "preserveNullAndEmptyArrays": True } },
                { "$group": { "_id": "$roles", "count": { "$sum": 1 } } }
            ]
            roles_data = await repository.aggregate_items(model_name, role_pipeline)
            
            roles_count = {}
            for r in roles_data:
                role_key = str(r.get("_id", "unknown"))
                if role_key == "None":
                    role_key = "unknown"
                roles_count[role_key] = r.get("count", 0)

            # DAU/MAU
            now_utc = datetime.now(timezone.utc)
            one_day_ago = now_utc - timedelta(days=1)
            thirty_days_ago = now_utc - timedelta(days=30)

            dau_pipeline = [
                { "$match": { "lastLoginAt": { "$gte": one_day_ago } } },
                { "$count": "count" }
            ]
            dau_res = await repository.aggregate_items(model_name, dau_pipeline)
            dau = dau_res[0]["count"] if dau_res else 0

            mau_pipeline = [
                { "$match": { "lastLoginAt": { "$gte": thirty_days_ago } } },
                { "$count": "count" }
            ]
            mau_res = await repository.aggregate_items(model_name, mau_pipeline)
            mau = mau_res[0]["count"] if mau_res else 0

            return JSONResponse({
                "total_users": total_users,
                "users_by_role": roles_count,
                "active_users": {
                    "daily": dau,
                    "monthly": mau
                }
            }, status_code=200)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/stats/custom/{metric_name}")
    async def get_custom_metric(metric_name: str):
        callback = LaiaMetricsRegistry.get_metric_callback(metric_name)
        if not callback:
            raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")
        
        try:
            result = await callback()
            return JSONResponse(result, status_code=200)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/stats/custom")
    async def list_custom_metrics():
        return JSONResponse({"metrics": LaiaMetricsRegistry.list_metrics()}, status_code=200)

    return router
