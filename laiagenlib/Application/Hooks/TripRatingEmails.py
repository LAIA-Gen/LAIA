from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional
from urllib.parse import urlencode

from .Lambdas.SendMailLambda import send_mail_lambda
from ...Domain.Shared.Utils.logger import _logger


DEFAULT_SUBJECT = "Valora la teva experiencia a MouCultura"
DEFAULT_TEMPLATE = "mail.valoracio.html"
DEFAULT_LOCALE = "ca"
DEFAULT_REVIEW_BASE_URL = "https://moucultura.cat/feedback"


async def send_trip_rating_emails(
    repository,
    smtp_config: dict,
    subject: str = DEFAULT_SUBJECT,
    template: str = DEFAULT_TEMPLATE,
    locale: str = DEFAULT_LOCALE,
    days_after_event: int = 2,
    now: Optional[datetime] = None,
    force: bool = False,
    dry_run: bool = False,
    review_base_url: Optional[str] = None,
    send_func: Callable[..., Awaitable[None]] = send_mail_lambda,
) -> dict:
    """
    Sends post-trip rating emails for completed MouCultura matches.

    The flow follows the current MouCultura match model:
    Match.completed -> Offer.userId (mouer) + Demand.userId (seeker),
    only when the related Event/Activity finished at least `days_after_event` ago.
    """
    current_time = _as_aware_utc(now or datetime.now(timezone.utc))
    cutoff = current_time - timedelta(days=days_after_event)
    review_base = _review_base_url(review_base_url, smtp_config)

    match_filters = {"status": "completed"}
    if not force:
        match_filters["ratingEmailSentAt"] = {"$exists": False}

    matches, _ = await repository.get_items(
        model_name="match",
        filters=match_filters,
        limit=1000,
    )

    sent_count = 0
    errors = []
    events_by_id = {}
    processed_match_ids = set()
    seen_recipients = set()

    for match in matches:
        match_id = _doc_id(match)
        if not match_id:
            errors.append("Match without id skipped")
            continue

        try:
            offer = await _find_by_id(repository, "offer", match.get("offerId"))
            demand = await _find_by_id(repository, "demand", match.get("requestId"))

            if not offer:
                errors.append(f"Match {match_id}: offer not found")
                continue
            if not demand:
                errors.append(f"Match {match_id}: demand not found")
                continue

            event = await _find_related_event(repository, offer)
            if not event:
                errors.append(f"Match {match_id}: related event/activity not found")
                continue

            event_end = _event_end_date(event)
            if not event_end:
                errors.append(f"Match {match_id}: related event has no final date")
                continue
            if event_end > cutoff:
                continue

            event_id = _doc_id(event)
            event_entry = events_by_id.setdefault(
                event_id,
                {
                    "eventId": event_id,
                    "eventName": event.get("title", ""),
                    "finalDate": event_end.isoformat(),
                    "matches": [],
                    "participants": [],
                    "mouers": [],
                },
            )

            match_entry = {
                "matchId": match_id,
                "offerId": _doc_id(offer),
                "demandId": _doc_id(demand),
                "recipients": [],
            }

            recipients = []
            mouer = await _find_by_id(repository, "user", offer.get("userId") or offer.get("owner"))
            seeker = await _find_by_id(repository, "user", demand.get("userId"))

            if mouer:
                recipients.append(("mouer", mouer))
            else:
                errors.append(f"Match {match_id}: mouer user not found")

            if seeker:
                recipients.append(("seeker", seeker))
            else:
                errors.append(f"Match {match_id}: seeker user not found")

            match_sent = 0
            for role, user in recipients:
                user_id = _doc_id(user)
                email = user.get("email", "")
                if not email:
                    errors.append(f"Match {match_id}: {role} {user_id} has no email")
                    continue

                recipient_key = (match_id, user_id, role)
                if recipient_key in seen_recipients:
                    continue
                seen_recipients.add(recipient_key)

                context = {
                    "username": user.get("name", ""),
                    "role": role,
                    "matchId": match_id,
                    "offerId": _doc_id(offer),
                    "demandId": _doc_id(demand),
                    "eventId": event_id,
                    "tripTitle": event.get("title", ""),
                    "reviewUrl": _build_review_url(review_base, match_id, user_id, role),
                }

                recipient_info = {
                    "id": user_id,
                    "name": user.get("name", ""),
                    "email": email,
                    "role": role,
                    "reviewUrl": context["reviewUrl"],
                }
                match_entry["recipients"].append(recipient_info)
                _append_unique(event_entry["participants"], recipient_info, "id")
                if role == "mouer":
                    _append_unique(event_entry["mouers"], recipient_info, "id")

                if dry_run:
                    continue

                try:
                    await send_func(
                        to=email,
                        subject=subject,
                        template=template,
                        context=context,
                        smtp_config=smtp_config,
                        locale=locale,
                    )
                    sent_count += 1
                    match_sent += 1
                except Exception as exc:
                    errors.append(f"Match {match_id}: failed for {email}: {exc}")

            event_entry["matches"].append(match_entry)

            if not dry_run and match_sent > 0:
                await repository.put_item(
                    "match",
                    match_id,
                    {"ratingEmailSentAt": current_time.isoformat()},
                )
                processed_match_ids.add(match_id)

        except Exception as exc:
            _logger.exception("Unexpected error processing match %s", match_id)
            errors.append(f"Match {match_id}: {exc}")

    events = list(events_by_id.values())
    return {
        "message": _result_message(sent_count, events, errors, dry_run),
        "sent_count": sent_count,
        "errors": errors,
        "count": len(events),
        "processed_match_ids": sorted(processed_match_ids),
        "events": events,
        "dry_run": dry_run,
    }


async def _find_related_event(repository, offer: dict) -> Optional[dict]:
    event_id = offer.get("eventId") or offer.get("activityId")
    if not event_id:
        return None

    event = await _find_by_id(repository, "event", event_id)
    if event:
        return event
    return await _find_by_id(repository, "activity", event_id)


async def _find_by_id(repository, model_name: str, item_id) -> Optional[dict]:
    if not item_id:
        return None

    candidates = [item_id, str(item_id)]
    for candidate in candidates:
        for field_name in ("id", "_id"):
            try:
                items, _ = await repository.get_items(
                    model_name=model_name,
                    filters={field_name: candidate},
                    limit=1,
                )
                if items:
                    return items[0]
            except Exception:
                continue
    return None


def _event_end_date(event: dict) -> Optional[datetime]:
    for field_name in ("finalDate", "endAt", "availabilityEndAt"):
        value = event.get(field_name)
        parsed = _parse_datetime(value)
        if parsed:
            return parsed
    return None


def _parse_datetime(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return _as_aware_utc(value)
    if isinstance(value, str) and value:
        normalized = value.replace(" ", "T")
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            return _as_aware_utc(datetime.fromisoformat(normalized))
        except ValueError:
            return None
    return None


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _doc_id(document: Optional[dict]) -> str:
    if not document:
        return ""
    value = document.get("id", document.get("_id", ""))
    return str(value) if value is not None else ""


def _review_base_url(review_base_url: Optional[str], smtp_config: dict) -> str:
    if review_base_url:
        return review_base_url
    configured = (smtp_config or {}).get("review_base_url") or (smtp_config or {}).get("frontend_url")
    if configured:
        return f"{configured.rstrip('/')}/feedback"
    return DEFAULT_REVIEW_BASE_URL


def _build_review_url(base_url: str, match_id: str, user_id: str, role: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'matchId': match_id, 'userId': user_id, 'role': role})}"


def _append_unique(items: list, item: dict, key: str):
    if not any(existing.get(key) == item.get(key) for existing in items):
        items.append(item)


def _result_message(sent_count: int, events: list, errors: list, dry_run: bool) -> str:
    prefix = "Trip rating dry run" if dry_run else "Trip rating email run"
    return f"{prefix}: {sent_count} sent, {len(events)} event(s), {len(errors)} error(s)"
