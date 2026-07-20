import importlib.util
import os
import re
from typing import Any, Optional

from fastapi import HTTPException

from ...Domain.Hooks.LambdaRegistry import get_lambda
from ...Domain.Shared.Utils.logger import _logger


async def execute_hooks(event: str, model, element: dict, smtp_config: dict = None, repository=None):
    """
    Executes hooks defined in a model x-hooks section.

    Supported events include postsave, preupdate, postupdate and postdelete.
    The returned dict may contain mutations made by script hooks.
    """
    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    hooks_config = extra.get("x-hooks", {})
    hook_list = hooks_config.get(event, [])

    if not hook_list:
        return element

    _logger.info(f"Executing {len(hook_list)} hook(s) for event '{event}' on {model.__name__}")

    for hook_def in hook_list:
        command_name = hook_def.get("command") or hook_def.get("lambda")
        has_script = "script" in hook_def
        script = hook_def.get("script")
        if command_name == "anonymous":
            has_script = True
            script = hook_def

        if not command_name and not has_script:
            _logger.warning(f"Hook without command or script in {model.__name__}, skipping")
            continue

        hook_body = script if isinstance(script, dict) else hook_def
        condition = hook_body.get("condition")
        if condition and not await _evaluate_condition(condition, element, repository):
            _logger.info(f"Hook condition '{condition}' not met, skipping")
            continue

        if has_script:
            if isinstance(script, str) and not hook_body.get("execute") and not hook_body.get("action"):
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
                )
                _logger.info(f"Hook script '{script}' executed successfully")
                continue

            execute = hook_body.get("execute") or hook_body.get("action")
            await _execute_script(execute, element, repository)
            _logger.info("Hook script executed successfully")
            continue

        try:
            lambda_func = get_lambda(command_name)
        except ValueError as e:
            _logger.error(str(e))
            continue

        params = {k: v for k, v in hook_def.items() if k not in ("command", "lambda", "condition")}
        expanded_params_list = await _expand_wildcard_params(params, element, repository)

        for resolved_params in expanded_params_list:
            resolved = await _resolve_all_params(resolved_params, element, repository)
            try:
                await lambda_func(**resolved, smtp_config=smtp_config)
                _logger.info(f"Hook command '{command_name}' executed successfully")
            except Exception as e:
                _logger.error(f"Hook command '{command_name}' failed for {model.__name__}: {e}")

    return element


async def _evaluate_condition(condition: str, element: dict, repository=None) -> bool:
    try:
        return bool(await _evaluate_expression(condition, element, repository))
    except Exception as exc:
        _logger.warning(f"Cannot evaluate condition '{condition}': {exc}")
        return False


async def _execute_script(execute: str, element: dict, repository=None):
    if not execute:
        return

    execute = execute.strip()
    if execute.startswith("HttpResponse"):
        status_match = re.search(r"status\s*:\s*(\d+)", execute)
        body_match = re.search(r"body\s*:\s*['\"]([^'\"]*)['\"]", execute)
        status_code = int(status_match.group(1)) if status_match else 409
        detail = body_match.group(1) if body_match else "Hook response"
        raise HTTPException(status_code=status_code, detail=detail)

    assignment = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*$", execute)
    if not assignment:
        _logger.warning(f"Cannot parse hook script: '{execute}'")
        return

    field_name, expression = assignment.groups()
    element[field_name] = await _evaluate_expression(expression, element, repository)


async def _execute_file_script(
    script: str,
    event: str,
    model,
    element: dict,
    hook_def: dict,
    params: dict,
    smtp_config: dict = None,
    repository=None,
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
        "smtp_config": smtp_config,
        "params": resolved_params,
        "hook": hook_def,
    }

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


async def _evaluate_expression(expression: str, element: dict, repository=None) -> Any:
    expression = str(expression).strip()

    if expression.lower() == "true":
        return True
    if expression.lower() == "false":
        return False

    query_values = {}
    expression = await _replace_query_expressions(expression, element, repository, query_values)
    expression = await _replace_mustache_expressions(expression, element, repository)
    expression = re.sub(r"(?<![!<>=])=(?![=])", "==", expression)
    expression = expression.replace("&&", " and ").replace("||", " or ")

    if expression in query_values:
        return query_values[expression]

    if re.match(r"^[A-Za-z_]\w*$", expression):
        return element.get(expression, [])

    safe_globals = {"__builtins__": {}}
    safe_locals = {
        "len": len,
        "True": True,
        "False": False,
        "None": None,
        "null": None,
        **query_values,
        **{k: v for k, v in element.items() if re.match(r"^[A-Za-z_]\w*$", str(k))},
    }
    return eval(expression, safe_globals, safe_locals)


async def _replace_query_expressions(expression: str, element: dict, repository=None, query_values: dict = None) -> str:
    query_values = query_values if query_values is not None else {}
    pattern = re.compile(r"QUERY\(([^()]*)\)(?:\.([A-Za-z_]\w*))?")

    while True:
        match = pattern.search(expression)
        if not match:
            return expression

        query_expr, projection = match.groups()
        items = await _execute_query(query_expr, element, repository)
        value = [item.get(projection) for item in items if projection in item] if projection else items
        key = f"__query_{len(query_values)}"
        query_values[key] = value
        expression = expression[:match.start()] + key + expression[match.end():]


async def _replace_mustache_expressions(expression: str, element: dict, repository=None) -> str:
    full_match = re.match(r"^\{\{(\S+)\}\}$", expression)
    if full_match:
        value = await _resolve_path(full_match.group(1), element, repository)
        return repr(value)

    replacements = []
    for match in re.finditer(r"\{\{(\S+?)\}\}", expression):
        value = await _resolve_path(match.group(1), element, repository)
        replacements.append((match.span(), repr(value)))

    for (start, end), replacement in reversed(replacements):
        expression = expression[:start] + replacement + expression[end:]
    return expression


async def _execute_query(query_expr: str, element: dict, repository=None) -> list:
    if not repository:
        return []

    clauses = [part.strip() for part in re.split(r"\s+&&\s+|\s+and\s+", query_expr) if part.strip()]
    if not clauses:
        return []

    model_name = None
    filters = {}
    post_filters = []

    for clause in clauses:
        match = re.match(r"^(?:(\w+)\.)?(\w+)\s*(==|!=|=)\s*(.+)$", clause)
        if not match:
            _logger.warning(f"Cannot parse QUERY clause: '{clause}'")
            return []

        clause_model, field_name, operator, raw_value = match.groups()
        if clause_model:
            model_name = model_name or clause_model.lower()

        value = await _evaluate_query_value(raw_value.strip(), element, repository)
        if operator in ("=", "=="):
            filters[field_name] = value
        else:
            post_filters.append((field_name, value))

    if not model_name:
        _logger.warning(f"QUERY without model name: '{query_expr}'")
        return []

    items, _ = await repository.get_items(model_name=model_name, filters=filters, limit=1000)

    for field_name, forbidden_value in post_filters:
        items = [item for item in items if str(item.get(field_name)) != str(forbidden_value)]
    return items


async def _evaluate_query_value(raw_value: str, element: dict, repository=None) -> Any:
    if re.match(r"^\{\{\S+\}\}$", raw_value):
        return await _resolve_path(raw_value[2:-2], element, repository)
    if (raw_value.startswith("'") and raw_value.endswith("'")) or (raw_value.startswith('"') and raw_value.endswith('"')):
        return raw_value[1:-1]
    if raw_value.lower() == "true":
        return True
    if raw_value.lower() == "false":
        return False
    try:
        return int(raw_value)
    except ValueError:
        return raw_value


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


async def _expand_wildcard_params(params: dict, element: dict, repository=None) -> list:
    wildcard_pattern = re.compile(r"\{\{(\w+)\.\*\.(\w+)\}\}")
    wildcard_field = None
    wildcard_subfield = None

    for value in params.values():
        values_to_check = value.values() if isinstance(value, dict) else [value]
        for nested_value in values_to_check:
            if isinstance(nested_value, str):
                match = wildcard_pattern.search(nested_value)
                if match:
                    wildcard_field = match.group(1)
                    wildcard_subfield = match.group(2)
                    break
        if wildcard_field:
            break

    if not wildcard_field:
        return [params]

    ids_list = element.get(wildcard_field, [])
    if not ids_list or not isinstance(ids_list, list):
        _logger.warning(f"Wildcard field '{wildcard_field}' is not a list or is empty")
        return []

    expanded = []
    for item_id in ids_list:
        referenced_data = None
        if repository:
            try:
                referenced_data = await _populate_reference(str(item_id), repository)
            except Exception as e:
                _logger.error(f"Failed to populate {wildcard_field} ID {item_id}: {e}")
                continue

        if not referenced_data:
            continue

        expanded.append(_replace_wildcard_in_params(params, wildcard_field, referenced_data))

    return expanded


def _replace_wildcard_in_params(params: dict, field: str, data: dict) -> dict:
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
