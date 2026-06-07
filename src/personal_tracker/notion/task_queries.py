from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from .client import DatabaseClient
from .models import Task


def today_filter(fields: dict[str, str], *, now: datetime, tz: ZoneInfo) -> dict[str, Any]:
    start = datetime.combine(now.astimezone(tz).date(), time.min, tzinfo=tz)
    end = datetime.combine(now.astimezone(tz).date(), time.max, tzinfo=tz)
    return {
        "and": [
            {"property": fields["time_mark"], "date": {"on_or_after": start.isoformat()}},
            {"property": fields["time_mark"], "date": {"on_or_before": end.isoformat()}},
        ]
    }


def find_task_by_name(
    client: DatabaseClient,
    fields: dict[str, str],
    name: str,
) -> Task | None:
    raw = client.retrieve_pages(
        filter={"property": fields["task_name"], "title": {"equals": name}},
    )
    if not raw:
        return None
    if len(raw) > 1:
        raise ValueError(f"Multiple tasks found with name {name!r} ({len(raw)} matches)")
    result = Task.from_data(raw[0], fields)
    assert isinstance(result, Task)
    return result
