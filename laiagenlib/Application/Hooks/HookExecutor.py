import re
from typing import Any, Optional

from ...Domain.Hooks.LambdaRegistry import get_lambda
from ...Domain.Shared.Utils.logger import _logger


async def execute_hooks(event: str, model, element: dict, smtp_config: dict = None, repository=None):
    """
    Executa els hooks definits al model per a un event concret.
    
    Args:
        event: "postsave", "postupdate", "postdelete"
        model: La classe del model Pydantic (amb model_config)
        element: L'element creat/actualitzat (dict)
        smtp_config: Configuració SMTP
        repository: Repositori per fer lookups (populate de relacions)
    """
    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    hooks_config = extra.get("x-hooks", {})
    hook_list = hooks_config.get(event, [])

    if not hook_list:
        return

    _logger.info(f"Executing {len(hook_list)} hook(s) for event '{event}' on {model.__name__}")

    for hook_def in hook_list:
        lambda_name = hook_def.get("lambda")
        if not lambda_name:
            _logger.warning(f"Hook without lambda name in {model.__name__}, skipping")
            continue

        # 1. Avaluar condició
        condition = hook_def.get("condition")
        if condition and not _evaluate_condition(condition, element):
            _logger.info(f"Hook condition '{condition}' not met, skipping")
            continue

        # 2. Obtenir lambda
        try:
            lambda_func = get_lambda(lambda_name)
        except ValueError as e:
            _logger.error(str(e))
            continue

        # 3. Resoldre paràmetres
        params = {k: v for k, v in hook_def.items() if k not in ("lambda", "condition")}
        
        # Comprovar si hi ha patró "wildcard" ({{acceptedUserIds.*.email}})
        # que implica iterar sobre una llista
        expanded_params_list = await _expand_wildcard_params(params, element, repository)

        # 4. Executar lambda per cada conjunt de paràmetres resolts
        for resolved_params in expanded_params_list:
            resolved = await _resolve_all_params(resolved_params, element, repository)
            try:
                await lambda_func(**resolved, smtp_config=smtp_config)
                _logger.info(f"Hook '{lambda_name}' executed successfully")
            except Exception as e:
                _logger.error(f"Hook '{lambda_name}' failed for {model.__name__}: {e}")


def _evaluate_condition(condition: str, element: dict) -> bool:
    """
    Avalua una condició simple contra l'element.
    Suporta: ==, !=
    Exemples: "statusOffer == 'full'", "isActive != true"
    """
    # Parse: camp operador valor
    match = re.match(r"^\s*(\w+)\s*(==|!=)\s*['\"]?([^'\"]+)['\"]?\s*$", condition)
    if not match:
        _logger.warning(f"Cannot parse condition: '{condition}'")
        return False

    field_name, operator, expected_value = match.groups()
    actual_value = element.get(field_name)

    if actual_value is None:
        return False

    # Convertir a string per comparar
    actual_str = str(actual_value)
    
    if operator == "==":
        return actual_str == expected_value
    elif operator == "!=":
        return actual_str != expected_value
    
    return False


async def _expand_wildcard_params(params: dict, element: dict, repository=None) -> list:
    """
    Si hi ha un paràmetre amb patró {{field.*.subfield}}, expandeix a N conjunts
    de paràmetres (un per cada element de la llista).
    Si no hi ha wildcards, retorna [params] directament.
    """
    wildcard_pattern = re.compile(r"\{\{(\w+)\.\*\.(\w+)\}\}")
    
    # Buscar si algun valor conté wildcards
    wildcard_field = None
    wildcard_subfield = None
    
    for key, value in params.items():
        if isinstance(value, str):
            match = wildcard_pattern.search(value)
            if match:
                wildcard_field = match.group(1)
                wildcard_subfield = match.group(2)
                break
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, str):
                    match = wildcard_pattern.search(v)
                    if match:
                        wildcard_field = match.group(1)
                        wildcard_subfield = match.group(2)
                        break

    if not wildcard_field:
        return [params]

    # Obtenir la llista d'IDs
    ids_list = element.get(wildcard_field, [])
    if not ids_list or not isinstance(ids_list, list):
        _logger.warning(f"Wildcard field '{wildcard_field}' is not a list or is empty")
        return []

    # Per cada ID, fer populate i crear un conjunt de paràmetres
    expanded = []
    for item_id in ids_list:
        # Fer lookup a la BD per obtenir les dades de l'element referenciat
        referenced_data = None
        if repository:
            try:
                referenced_data = await _populate_reference(str(item_id), repository)
            except Exception as e:
                _logger.error(f"Failed to populate {wildcard_field} ID {item_id}: {e}")
                continue

        if not referenced_data:
            continue

        # Crear còpia dels params substituint wildcards
        expanded_params = _replace_wildcard_in_params(
            params, wildcard_field, referenced_data
        )
        expanded.append(expanded_params)

    return expanded


def _replace_wildcard_in_params(params: dict, field: str, data: dict) -> dict:
    """Substitueix qualsevol {{field.*.subfield}} pels valors reals de data[subfield]."""
    import copy
    new_params = copy.deepcopy(params)
    pattern = re.compile(f"\\{{\\{{{field}\\.\\*\\.(\\w+)\\}}\\}}")

    def replacer(match):
        sub = match.group(1)
        return str(data.get(sub, ""))

    for key, value in new_params.items():
        if isinstance(value, str):
            new_params[key] = pattern.sub(replacer, value)
        elif isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, str):
                    value[k] = pattern.sub(replacer, v)

    return new_params


async def _resolve_all_params(params: dict, element: dict, repository=None) -> dict:
    """
    Resol totes les variables {{camp}} dins dels paràmetres.
    """
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str):
            resolved[key] = await _resolve_value(value, element, repository)
        elif isinstance(value, dict):
            resolved[key] = {}
            for k, v in value.items():
                if isinstance(v, str):
                    resolved[key][k] = await _resolve_value(v, element, repository)
                else:
                    resolved[key][k] = v
        else:
            resolved[key] = value
    return resolved


async def _resolve_value(value: str, element: dict, repository=None) -> Any:
    """
    Resol una variable {{camp}} o {{camp.subcamp}} pel seu valor real.
    
    - {{email}} → element["email"]
    - {{_self}} → tot l'element
    - {{name}} → element["name"]
    - {{userId.email}} → lookup a BD per obtenir User i retornar email
    """
    # Patró: tota la cadena és una variable
    full_match = re.match(r"^\{\{(\S+)\}\}$", value)
    if not full_match:
        # Pot tenir variables dins del text: "Hola {{name}}"
        def replace_var(m):
            var_name = m.group(1)
            if var_name == "_self":
                return str(element)
            if "." in var_name:
                # No podem fer async dins de re.sub, retornem placeholder
                return str(element.get(var_name.split(".")[0], ""))
            return str(element.get(var_name, ""))
        
        result = re.sub(r"\{\{(\S+?)\}\}", replace_var, value)
        return result

    var_path = full_match.group(1)

    # Cas especial: _self
    if var_path == "_self":
        return element

    # Cas simple: camp directe
    if "." not in var_path:
        return element.get(var_path, value)

    # Cas compost: camp.subcamp (necessita populate)
    parts = var_path.split(".")
    field_name = parts[0]
    sub_field = parts[1]

    ref_id = element.get(field_name)
    if not ref_id:
        return value

    # Fer lookup a la BD
    if repository:
        try:
            referenced = await _populate_reference(str(ref_id), repository)
            if referenced:
                return referenced.get(sub_field, value)
        except Exception as e:
            _logger.error(f"Failed to resolve {var_path}: {e}")

    return value


async def _populate_reference(ref_id: str, repository) -> Optional[dict]:
    """
    Busca un element per ID a la BD (prova col·leccions comunes).
    """
    # Prova primer amb 'user' (el cas més comú)
    for collection in ["user", "offer", "demand", "activity", "site", "vehicle"]:
        try:
            items, _ = await repository.get_items(
                model_name=collection,
                filters={"_id": ref_id},
                limit=1
            )
            if items:
                return items[0]
        except Exception:
            continue
    return None
