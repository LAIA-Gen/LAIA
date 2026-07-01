from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
from typing import TypeVar, Type, Union
from copy import deepcopy
from inspect import Parameter, signature
import re
import os
import yaml
from bson import ObjectId
from bson.errors import InvalidId

from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from ...Domain.Shared.Utils.SerializeBson import serialize_bson
from .MetricsRegistry import LaiaMetricsRegistry
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)
PLACEHOLDER_RE = re.compile(r"^{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}$")
INTERPOLATION_RE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")


def _cast_metric_param(name: str, value: str, config: dict):
    param_type = str(config.get("type", "string")).lower()

    if param_type in ("objectid", "object_id"):
        try:
            return ObjectId(value)
        except InvalidId as e:
            raise HTTPException(status_code=400, detail=f"Invalid ObjectId for query param '{name}': {str(e)}")

    if param_type in ("int", "integer"):
        try:
            return int(value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid integer for query param '{name}'")

    if param_type in ("float", "number"):
        try:
            return float(value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid number for query param '{name}'")

    if param_type in ("bool", "boolean"):
        return str(value).lower() in ("1", "true", "yes", "y", "on")

    return value


def _build_metric_context(query_params: dict, params_config: dict):
    context = dict(query_params)

    for name, config in (params_config or {}).items():
        if config is None:
            config = {}

        if name not in query_params:
            if config.get("required", False):
                raise HTTPException(status_code=400, detail=f"Missing required query param '{name}'")
            if "default" in config:
                context[name] = config["default"]
            continue

        context[name] = _cast_metric_param(name, query_params[name], config)

    return context


def _resolve_metric_placeholders(value, context: dict):
    if isinstance(value, dict):
        return {key: _resolve_metric_placeholders(item, context) for key, item in value.items()}

    if isinstance(value, list):
        return [_resolve_metric_placeholders(item, context) for item in value]

    if isinstance(value, str):
        exact_match = PLACEHOLDER_RE.match(value)
        if exact_match:
            name = exact_match.group(1)
            if name not in context:
                raise HTTPException(status_code=400, detail=f"Missing query param '{name}'")
            return context[name]

        def replace_match(match):
            name = match.group(1)
            if name not in context:
                raise HTTPException(status_code=400, detail=f"Missing query param '{name}'")
            return str(context[name])

        return INTERPOLATION_RE.sub(replace_match, value)

    return value


async def _execute_metric_callback(callback, request: Request):
    query_params = dict(request.query_params)
    parameters = signature(callback).parameters

    if not parameters:
        return await callback()

    if any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values()):
        return await callback(**query_params)

    if query_params and all(name in parameters for name in query_params):
        return await callback(**query_params)

    if "request" in parameters:
        return await callback(request)

    if "query_params" in parameters:
        return await callback(query_params)

    return await callback(query_params)

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
                    params_config = m.get("params", {})

                    def make_count_callback(col, flt, metric_name, param_cfg):
                        async def metric_callback(query_params=None):
                            context = _build_metric_context(query_params or {}, param_cfg)
                            resolved_filters = _resolve_metric_placeholders(deepcopy(flt), context)
                            count = repository.db[col].count_documents(resolved_filters)
                            return {metric_name: count}
                        return metric_callback
                    
                    LaiaMetricsRegistry.register_metric(name, make_count_callback(collection, filters, name, params_config))
                    
                elif m_type == "aggregate":
                    pipeline = m.get("pipeline", [])
                    params_config = m.get("params", {})

                    def make_agg_callback(col, pipe, metric_name, param_cfg):
                        async def metric_callback(query_params=None):
                            context = _build_metric_context(query_params or {}, param_cfg)
                            resolved_pipeline = _resolve_metric_placeholders(deepcopy(pipe), context)
                            res = list(repository.db[col].aggregate(resolved_pipeline))
                            return {metric_name: res}
                        return metric_callback
                    
                    LaiaMetricsRegistry.register_metric(name, make_agg_callback(collection, pipeline, name, params_config))

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
            
            collection = repository.db[model_name]
            
            # Total users
            total_users = collection.count_documents({})

            # Users by role
            role_pipeline = [
                {"$addFields": {"roles_obj": {"$map": {"input": { "$ifNull": ["$roles", []] }, "as": "r", "in": { "$toObjectId": "$$r" }}}}}, 
                { "$lookup": { "from": "role", "localField": "roles_obj", "foreignField": "_id", "as": "role_doc" } },
                { "$unwind": { "path": "$role_doc", "preserveNullAndEmptyArrays": True } },
                { "$group": { "_id": "$role_doc.name", "count": { "$sum": 1 } } }
            ]
            roles_data = list(collection.aggregate(role_pipeline))
            
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
            dau_res = list(collection.aggregate(dau_pipeline))
            dau = dau_res[0]["count"] if dau_res else 0

            mau_pipeline = [
                { "$match": { "lastLoginAt": { "$gte": thirty_days_ago } } },
                { "$count": "count" }
            ]
            mau_res = list(collection.aggregate(mau_pipeline))
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
    async def get_custom_metric(metric_name: str, request: Request):
        return await _get_custom_metric_response(metric_name, request)

    @router.get("/stats/custom/{metric_name}/by-activity")
    async def get_custom_metric_by_activity(
            metric_name: str,
            request: Request,
            activityId: str = Query(..., description="Activity id used to filter this custom metric")):
        return await _get_custom_metric_response(metric_name, request)

    async def _get_custom_metric_response(metric_name: str, request: Request):
        callback = LaiaMetricsRegistry.get_metric_callback(metric_name)
        if not callback:
            raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")
        
        try:
            result = await _execute_metric_callback(callback, request)
            return JSONResponse(serialize_bson(result), status_code=200)
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/stats/custom")
    async def list_custom_metrics():
        return JSONResponse({"metrics": LaiaMetricsRegistry.list_metrics()}, status_code=200)

    return router
