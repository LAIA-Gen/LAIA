import os
from ....Domain.Shared.Utils.logger import _logger

def create_routes_file(path: str):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write("""from fastapi import APIRouter

router = APIRouter(tags=["Extra Routes"])

__all__ = ['router']""")
        _logger.info(f"Routes file created at {path}")
    else:
        _logger.info(f"Routes file already exists at {path}")
        