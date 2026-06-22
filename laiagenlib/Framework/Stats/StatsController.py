from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
from typing import TypeVar, Type, Union
import os
import yaml

from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from .MetricsRegistry import LaiaMetricsRegistry
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def StatsController(
        repository: ModelRepository,
        user_model: Union[Type[T], str] = None,
        metrics_file: str = None):
    router = APIRouter(tags=["Stats"])

    if metrics_file and os.path.exists(metrics_file):
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            metrics = data.get("metrics", []) if data else []
            for m in metrics:
                name = m.get("name")
                collection = m.get("collection")
                m_type = m.get("type", "count")
                
                if not name or not collection:
                    continue
                
                if m_type == "count":
                    filters = m.get("filters", {})
                    def make_count_callback(col, flt, metric_name):
                        async def metric_callback():
                            count = repository.db[col].count_documents(flt)
                            return {metric_name: count}
                        return metric_callback
                    
                    LaiaMetricsRegistry.register_metric(name, make_count_callback(collection, filters, name))
                    
                elif m_type == "aggregate":
                    pipeline = m.get("pipeline", [])
                    def make_agg_callback(col, pipe, metric_name):
                        async def metric_callback():
                            res = await repository.aggregate_items(col, pipe)
                            return {metric_name: res}
                        return metric_callback
                    
                    LaiaMetricsRegistry.register_metric(name, make_agg_callback(collection, pipeline, name))

        except Exception as e:
            _logger.error(f"Failed to load metrics from {metrics_file}: {str(e)}")


    @router.get("/stats/users")
    async def get_users_stats():
        if not user_model:
            raise HTTPException(status_code=500, detail="user_model not configured for StatsController")
        
        try:
            model_name = (
                user_model.lower()
                if isinstance(user_model, str)
                else user_model.__name__.lower()
            )
            
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
