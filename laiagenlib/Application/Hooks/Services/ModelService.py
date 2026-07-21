from typing import Any, Optional


class ModelService:
    model_name: str = ""

    def __init__(self, repository=None, model_name: str = ""):
        self.repository = repository
        self.model_name = model_name or self.model_name

    async def get_by_id(self, item_id: Any, model_name: str = "") -> Optional[dict]:
        if not item_id or not self.repository:
            return None

        collection = model_name or self.model_name
        if not collection:
            return None

        item_id = str(item_id)
        try:
            return await self.repository.get_item(collection, item_id)
        except Exception:
            pass

        try:
            items, _ = await self.repository.get_items(
                model_name=collection,
                filters={"_id": item_id},
                limit=1,
            )
        except Exception:
            return None
        return items[0] if items else None

    async def find(self, filters: dict = None, limit: int = 1000, model_name: str = "") -> list:
        if not self.repository:
            return []

        collection = model_name or self.model_name
        if not collection:
            return []

        try:
            items, _ = await self.repository.get_items(
                model_name=collection,
                filters=filters or {},
                limit=limit,
            )
        except Exception:
            return []
        return items

    async def first(self, filters: dict = None, model_name: str = "") -> Optional[dict]:
        items = await self.find(filters=filters, limit=1, model_name=model_name)
        return items[0] if items else None


class UserService(ModelService):
    model_name = "user"

    def get_locale(self, user: dict = None, default: str = "ca") -> str:
        user = user or {}
        explicit_locale = (
            user.get("preferredLanguage")
            or user.get("preferredLocale")
            or user.get("locale")
            or user.get("language")
        )
        if explicit_locale:
            return _normalize_locale(explicit_locale, default)

        languages = user.get("languages") or []
        if isinstance(languages, list) and languages:
            first_language = languages[0]
            if isinstance(first_language, dict):
                first_language = first_language.get("code") or first_language.get("id") or first_language.get("name")
            if first_language:
                return _normalize_locale(first_language, default)

        return default


class OfferService(ModelService):
    model_name = "offer"


class DemandService(ModelService):
    model_name = "demand"


class MatchService(ModelService):
    model_name = "match"


def _normalize_locale(locale: Any, default: str = "ca") -> str:
    locale = str(locale or default).strip().replace("-", "_")
    if not locale:
        return default

    language = locale.split("_", 1)[0].lower()
    if language == "en":
        return "en_US"
    if language == "es":
        return "es"
    if language == "ca":
        return "ca"
    return language
