from __future__ import annotations

import unicodedata
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from .client import DatabaseClient
from .models import Task


def _normalize_for_search(text: str) -> str:
    """Fold case and strip diacritics so search ignores accents.

    NFD decomposition splits most accented Latin letters into a base letter
    plus combining marks (category ``Mn``), which we drop. Vietnamese ``đ``/``Đ``
    has no canonical decomposition, so it is replaced explicitly.
    """
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.casefold().replace("đ", "d")


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


def search_tasks_by_title(
    client: DatabaseClient,
    fields: dict[str, str],
    query: str,
) -> list[Task]:
    # Match every whitespace-separated token against the title (AND), so a
    # multi-word query like "học kỹ thuật" still finds "Học các kỹ thuật harness"
    # where the words are not contiguous. Both query and title are normalized
    # (case- and accent-insensitive) so "hoc ky thuat" matches too.
    #
    # Notion's `contains` filter is server-side and accent-sensitive, so it
    # cannot honor the normalization — we fetch all tasks and filter here.
    needles = [_normalize_for_search(token) for token in query.split()]
    if not needles:
        return []
    raw = client.retrieve_pages()
    result = Task.from_data(raw, fields)
    task_list = result if isinstance(result, list) else [result]
    return [
        t
        for t in task_list
        if all(
            needle in _normalize_for_search(t.task_name or "") for needle in needles
        )
    ]
