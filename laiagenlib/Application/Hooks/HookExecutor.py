import importlib.util
import os
import re
from typing import Any, Optional

from .Services import create_hook_services
from ...Domain.Shared.Utils.logger import _logger


async def execute_hooks(event: str, model, element: dict, smtp_config: dict = None, repository=None, context_extra: dict = None):
    """
    Executes file-based hooks defined in a model x-hooks section.

    Hook YAML must use the new script form:

        x-hooks:
          postupdate:
            - script: offer/update_offer_status
              params:
                template: offer-confirmed

    LAIA loads the script from hooks_dir and calls async def run(context).
    The returned dict, if any, is merged into element.
    """
    hook_list = _get_hook_list(model, event)
    if not hook_list:
        return element

    _logger.info(f"Executing {len(hook_list)} hook(s) for event '{event}' on {model.__name__}")

    for hook_def in hook_list:
        script = hook_def.get("script")
        if not isinstance(script, str) or not script.strip():
            _logger.warning(f"Hook without file script in {model.__name__}, skipping")
            continue

        params = hook_def.get("params", {})
        await _execute_file_script(
            script,
            event=event,
            model=model,
            element=element,
            hook_def=hook_def,
            params=params,
            smtp_config=smtp_config,
            repository=repository,
            context_extra=context_extra,
        )
        _logger.info(f"Hook script '{script}' executed successfully")

    return element


def _get_hook_list(model, event: str) -> list:
    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    hooks_config = extra.get("x-hooks", {})
    if event in hooks_config:
        return hooks_config[event]

    normalized_event = event.lower()
    for configured_event, hook_list in hooks_config.items():
        if str(configured_event).lower() == normalized_event:
            return hook_list
    return []


async def _execute_file_script(
    script: str,
    event: str,
    model,
    element: dict,
    hook_def: dict,
    params: dict,
    smtp_config: dict = None,
    repository=None,
    context_extra: dict = None,
):
    hooks_dir = (smtp_config or {}).get("hooks_dir") or "hooks"
    script_path = _resolve_script_path(hooks_dir, script)
    module = _load_script_module(script_path)
    run_func = getattr(module, "run", None)
    if not run_func:
        raise ValueError(f"Hook script '{script}' must define a run(context) function")

    resolved_params = await _resolve_all_params(params or {}, element, repository)
    context = {
        "event": event,
        "model": model,
        "element": element,
        "repository": repository,
        "services": create_hook_services(repository, smtp_config),
        "smtp_config": smtp_config,
        "params": resolved_params,
        "hook": hook_def,
    }
    if context_extra:
        context.update(context_extra)

    result = run_func(context)
    if hasattr(result, "__await__"):
        result = await result

    if isinstance(result, dict):
        element.update(result)


def _resolve_script_path(hooks_dir: str, script: str) -> str:
    script_name = script.replace("\\", "/").strip("/")
    if not script_name.endswith(".py"):
        script_name = f"{script_name}.py"

    root = os.path.abspath(hooks_dir)
    path = os.path.abspath(os.path.join(root, *script_name.split("/")))
    if os.path.commonpath([root, path]) != root:
        raise ValueError(f"Hook script path escapes hooks directory: {script}")
    if not os.path.exists(path):
        raise ValueError(f"Hook script not found: {path}")
    return path


def _load_script_module(script_path: str):
    module_name = "laiagen_hook_" + re.sub(r"\W+", "_", script_path)
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if not spec or not spec.loader:
        raise ValueError(f"Cannot load hook script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _resolve_all_params(params: dict, element: dict, repository=None) -> dict:
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
    full_match = re.match(r"^\{\{(\S+)\}\}$", value)
    if not full_match:
        result = value
        replacements = []
        for match in re.finditer(r"\{\{(\S+?)\}\}", value):
            resolved = await _resolve_path(match.group(1), element, repository)
            replacements.append((match.span(), "" if resolved is None else str(resolved)))
        for (start, end), replacement in reversed(replacements):
            result = result[:start] + replacement + result[end:]
        return result

    var_path = full_match.group(1)
    resolved = await _resolve_path(var_path, element, repository)
    return value if resolved is None else resolved


async def _resolve_path(path: str, element: dict, repository=None) -> Any:
    if path == "_self":
        return element

    current_value: Any = element
    for part in path.split("."):
        if isinstance(current_value, dict):
            current_value = current_value.get(part)
            continue

        if isinstance(current_value, list):
            return [item.get(part) for item in current_value if isinstance(item, dict) and part in item]

        if current_value and repository:
            referenced = await _populate_reference(str(current_value), repository)
            current_value = referenced.get(part) if referenced else None
            continue

        return None

    return current_value


async def _populate_reference(ref_id: str, repository) -> Optional[dict]:
    for collection in ["user", "offer", "demand", "match", "activity", "site", "vehicle"]:
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
