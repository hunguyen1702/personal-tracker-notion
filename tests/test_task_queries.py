from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from personal_tracker.notion.task_queries import (
    find_task_by_name,
    search_tasks_by_title,
    today_filter,
)

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


def test_search_tasks_by_title_returns_empty_when_no_match():
    client = MagicMock()
    client.retrieve_pages.return_value = [_page("p-1", "Write report")]
    assert search_tasks_by_title(client, FIELDS, "Read") == []


def test_search_tasks_by_title_returns_matching_tasks():
    client = MagicMock()
    client.retrieve_pages.return_value = [
        _page("p-1", "Read paper"),
        _page("p-2", "Write report"),
    ]
    tasks = search_tasks_by_title(client, FIELDS, "Read")
    assert [t.notion_object_id for t in tasks] == ["p-1"]


def test_search_tasks_by_title_is_case_insensitive():
    client = MagicMock()
    client.retrieve_pages.return_value = [_page("p-1", "Read BOOK")]
    tasks = search_tasks_by_title(client, FIELDS, "book")
    assert [t.notion_object_id for t in tasks] == ["p-1"]


def test_search_tasks_by_title_strips_whitespace():
    client = MagicMock()
    client.retrieve_pages.return_value = [_page("p-1", "Read")]
    tasks = search_tasks_by_title(client, FIELDS, "  read  ")
    assert [t.notion_object_id for t in tasks] == ["p-1"]


def test_search_tasks_by_title_empty_query_returns_empty_without_api_call():
    client = MagicMock()
    assert search_tasks_by_title(client, FIELDS, "") == []
    assert search_tasks_by_title(client, FIELDS, "   ") == []
    client.retrieve_pages.assert_not_called()


def test_search_tasks_by_title_matches_non_contiguous_tokens():
    client = MagicMock()
    client.retrieve_pages.return_value = [_page("p-1", "Học các kỹ thuật harness")]
    tasks = search_tasks_by_title(client, FIELDS, "học kỹ thuật")
    assert [t.notion_object_id for t in tasks] == ["p-1"]


def test_search_tasks_by_title_fetches_without_text_filter():
    # Normalization is accent-insensitive, which Notion's server-side filter
    # cannot honor, so search must fetch all tasks and filter client-side.
    client = MagicMock()
    client.retrieve_pages.return_value = []
    search_tasks_by_title(client, FIELDS, "học kỹ thuật")
    assert client.retrieve_pages.call_args.kwargs.get("filter") is None


def test_search_tasks_by_title_ignores_diacritics():
    client = MagicMock()
    client.retrieve_pages.return_value = [_page("p-1", "Học các kỹ thuật harness")]
    tasks = search_tasks_by_title(client, FIELDS, "hoc ky thuat")
    assert [t.notion_object_id for t in tasks] == ["p-1"]


def test_search_tasks_by_title_handles_d_with_stroke():
    client = MagicMock()
    client.retrieve_pages.return_value = [_page("p-1", "Đón Gạo đi học")]
    tasks = search_tasks_by_title(client, FIELDS, "don gao")
    assert [t.notion_object_id for t in tasks] == ["p-1"]


def test_search_tasks_by_title_requires_all_tokens():
    client = MagicMock()
    # Notion's AND of `contains` could over-match if a token appears elsewhere;
    # the client-side post-filter must still require every token in the title.
    client.retrieve_pages.return_value = [_page("p-1", "Học tiếng Anh")]
    assert search_tasks_by_title(client, FIELDS, "học kỹ thuật") == []
