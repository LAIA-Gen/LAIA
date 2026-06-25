from ...Domain.Shared.Utils.logger import _logger

_registry: dict = {}


def register_lambda(name: str, func):
    """Registra una lambda (funció) amb un nom per poder-la invocar des dels hooks."""
    _registry[name] = func
    _logger.info(f"Lambda '{name}' registered in hook system")


def get_lambda(name: str):
    """Obté una lambda registrada pel seu nom."""
    func = _registry.get(name)
    if not func:
        raise ValueError(f"Lambda '{name}' is not registered. Available: {list(_registry.keys())}")
    return func


def list_lambdas() -> list:
    """Retorna els noms de totes les lambdes registrades."""
    return list(_registry.keys())
