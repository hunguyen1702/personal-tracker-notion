from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .client import DatabaseClient
from .models import Task


def today_filter(fields: dict[str, str], *, now: datetime, tz: ZoneInfo) -> dict[str, Any]:
    local_date = now.astimezone(tz).date().isoformat()
    return {
        "property": fields["time_mark"],
        "date": {"equals": local_date},
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
