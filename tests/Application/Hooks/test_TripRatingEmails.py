from datetime import datetime, timezone

import pytest

from laiagenlib.Application.Hooks.TripRatingEmails import send_trip_rating_emails


class FakeRepository:
    def __init__(self):
        self.collections = {
            "match": [
                {
                    "id": "match-1",
                    "offerId": "offer-1",
                    "requestId": "demand-1",
                    "status": "completed",
                }
            ],
            "offer": [
                {
                    "id": "offer-1",
                    "activityId": "event-1",
                    "userId": "mouer-1",
                }
            ],
            "demand": [
                {
                    "id": "demand-1",
                    "userId": "seeker-1",
                }
            ],
            "event": [
                {
                    "id": "event-1",
                    "title": "Concert solidari",
                    "finalDate": "2026-06-20T10:00:00+00:00",
                }
            ],
            "activity": [],
            "user": [
                {
                    "id": "mouer-1",
                    "name": "Marta",
                    "email": "marta@example.com",
                },
                {
                    "id": "seeker-1",
                    "name": "Pau",
                    "email": "pau@example.com",
                },
            ],
        }
        self.updates = []

    async def get_items(self, model_name, skip=0, limit=10, filters=None, orders=None, populate=None):
        filters = filters or {}
        items = [
            item for item in self.collections.get(model_name, [])
            if self._matches_filters(item, filters)
        ]
        return items[skip:skip + limit], len(items)

    async def put_item(self, model_name, item_id, update_fields):
        self.updates.append((model_name, item_id, update_fields))
        for item in self.collections.get(model_name, []):
            if item.get("id") == item_id or item.get("_id") == item_id:
                item.update(update_fields)
                return item
        raise ValueError(f"{model_name} {item_id} not found")

    def _matches_filters(self, item, filters):
        for key, expected in filters.items():
            if isinstance(expected, dict) and "$exists" in expected:
                exists = key in item
                if exists != expected["$exists"]:
                    return False
                continue
            if item.get(key) != expected:
                return False
        return True


@pytest.mark.asyncio
async def test_send_trip_rating_emails_sends_to_mouer_and_seeker():
    repo = FakeRepository()
    sent = []

    async def fake_send(**kwargs):
        sent.append(kwargs)

    result = await send_trip_rating_emails(
        repository=repo,
        smtp_config={"host": "smtp.example.com", "frontend_url": "https://app.example.com"},
        now=datetime(2026, 6, 23, 10, tzinfo=timezone.utc),
        send_func=fake_send,
    )

    assert result["sent_count"] == 2
    assert {email["to"] for email in sent} == {"marta@example.com", "pau@example.com"}
    assert sent[0]["template"] == "mail.valoracio.html"
    assert all("reviewUrl" in email["context"] for email in sent)
    by_recipient = {email["to"]: email for email in sent}
    mouer_context = by_recipient["marta@example.com"]["context"]
    seeker_context = by_recipient["pau@example.com"]["context"]
    assert mouer_context["role"] == "mouer"
    assert mouer_context["ratedUserName"] == "Pau"
    assert mouer_context["ratedUserRole"] == "seeker"
    assert "reviewerId=mouer-1" in mouer_context["reviewUrl"]
    assert "ratedUserId=seeker-1" in mouer_context["reviewUrl"]
    assert seeker_context["role"] == "seeker"
    assert seeker_context["ratedUserName"] == "Marta"
    assert seeker_context["ratedUserRole"] == "mouer"
    assert by_recipient["marta@example.com"]["subject"] == "Valora la teva experiència amb Pau"
    assert by_recipient["pau@example.com"]["subject"] == "Valora la teva experiència amb Marta"
    assert repo.updates == [
        ("match", "match-1", {"ratingEmailSentAt": "2026-06-23T10:00:00+00:00"})
    ]


@pytest.mark.asyncio
async def test_send_trip_rating_emails_dry_run_does_not_send_or_mark():
    repo = FakeRepository()
    sent = []

    async def fake_send(**kwargs):
        sent.append(kwargs)

    result = await send_trip_rating_emails(
        repository=repo,
        smtp_config={"host": "smtp.example.com"},
        now=datetime(2026, 6, 23, 10, tzinfo=timezone.utc),
        dry_run=True,
        send_func=fake_send,
    )

    assert result["dry_run"] is True
    assert result["sent_count"] == 0
    assert len(result["events"]) == 1
    assert len(result["events"][0]["matches"][0]["recipients"]) == 2
    assert sent == []
    assert repo.updates == []


@pytest.mark.asyncio
async def test_send_trip_rating_emails_skips_recent_events():
    repo = FakeRepository()
    repo.collections["event"][0]["finalDate"] = (
        datetime(2026, 6, 22, 10, tzinfo=timezone.utc).isoformat()
    )
    sent = []

    async def fake_send(**kwargs):
        sent.append(kwargs)

    result = await send_trip_rating_emails(
        repository=repo,
        smtp_config={"host": "smtp.example.com"},
        now=datetime(2026, 6, 23, 10, tzinfo=timezone.utc),
        send_func=fake_send,
    )

    assert result["sent_count"] == 0
    assert result["events"] == []
    assert sent == []
