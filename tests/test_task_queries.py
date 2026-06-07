from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from personal_tracker.notion.task_queries import find_task_by_name, today_filter

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

FIELDS = {
    "task_name": "What to do",
    "time_mark": "Do on",
    "is_done": "Done?",
    "recurring_type": "Repeat",
}


def test_today_filter_uses_local_date():
    # 00:30 UTC == 07:30 ICT, still the same day in ICT.
    now = datetime(2026, 6, 2, 0, 30, tzinfo=ZoneInfo("UTC"))
    f = today_filter(FIELDS, now=now, tz=TZ)
    assert f == {
        "and": [
            {"property": "Do on", "date": {"on_or_after": "2026-06-02T00:00:00+07:00"}},
            {"property": "Do on", "date": {"on_or_before": "2026-06-02T23:59:59.999999+07:00"}},
        ]
    }


def _page(id_: str, name: str) -> dict:
    return {
        "id": id_,
        "properties": {
            "What to do": {"type": "title", "title": [{"plain_text": name}]},
            "Do on": {"type": "date", "date": None},
            "Done?": {"type": "checkbox", "checkbox": False},
            "Repeat": {"type": "select", "select": {"name": "once"}},
        },
    }


def test_find_task_by_name_returns_none_when_empty():
    client = MagicMock()
    client.retrieve_pages.return_value = []
    assert find_task_by_name(client, FIELDS, "Missing") is None


def test_find_task_by_name_returns_task_when_one_match():
    client = MagicMock()
    client.retrieve_pages.return_value = [_page("p-1", "Read")]
    task = find_task_by_name(client, FIELDS, "Read")
    assert task is not None
    assert task.notion_object_id == "p-1"
    assert task.task_name == "Read"


def test_find_task_by_name_raises_when_ambiguous():
    client = MagicMock()
    client.retrieve_pages.return_value = [_page("a", "Read"), _page("b", "Read")]
    with pytest.raises(ValueError):
        find_task_by_name(client, FIELDS, "Read")
