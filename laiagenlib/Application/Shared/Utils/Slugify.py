import re, unicodedata

from laiagenlib.Domain.LaiaBaseModel.ModelRepository import ModelRepository
from laiagenlib.Domain.Shared.Utils.logger import _logger

def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

async def nicename_exists(model_name: str, repository: ModelRepository, nicename: str) -> bool:
    """
    Comprueba si existe ya un documento con ese nicename.
    """
    data = await repository.get_items(
        model_name,
        skip=0,
        limit=1,
        filters={"nicename": nicename}
    )
    if isinstance(data, tuple) and len(data) >= 1:
        items = data[0]
        return len(items) > 0
    if isinstance(data, dict) and "items" in data:
        return len(data["items"]) > 0
    if isinstance(data, (list, tuple)):
        return len(data) > 0
    return False

async def ensure_unique_nicename(raw_nicename: str, model_name: str, repository: ModelRepository) -> str:
    base = raw_nicename
    nicename = base
    i = 1
    MAX_TRIES = 1000
    while await nicename_exists(model_name, repository, nicename):
        if i > MAX_TRIES:
            raise RuntimeError(f"No se pudo generar nicename único para {base}")
        _logger.error(f"Nicename {nicename} ya existe, probando siguiente…")
        nicename = f"{base}-{i}"
        i += 1
    return nicename
