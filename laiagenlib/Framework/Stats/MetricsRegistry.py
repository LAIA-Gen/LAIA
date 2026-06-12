from typing import Callable, Dict, Any, Awaitable
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

class LaiaMetricsRegistry:
    _registry: Dict[str, Callable[[], Awaitable[Any]]] = {}

    @classmethod
    def register_metric(cls, name: str, callback: Callable[[], Awaitable[Any]]):
        """
        Registers an async function that returns data for a specific metric name.
        """
        cls._registry[name] = callback

    @classmethod
    def get_metric_callback(cls, name: str) -> Callable[[], Awaitable[Any]]:
        return cls._registry.get(name)

    @classmethod
    def list_metrics(cls) -> list[str]:
        return list(cls._registry.keys())
