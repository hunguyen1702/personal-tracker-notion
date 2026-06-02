from datetime import datetime, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from personal_tracker.config import Settings
from personal_tracker.notion.task_polling import TaskPolling

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

DEFINITION_FIELDS = {
    "task_name": "What to do",
    "time_mark": "Do on",
    "end_time": "Do on end",
    "deadline": "Deadline",
    "is_done": "Done?",
    "recurring_type": "Repeat",
    "remind": "Remind",
}


def make_settings(skip_time: bool = False) -> Settings:
    return Settings(
        data={
            "notion": {
                "definition_fields": DEFINITION_FIELDS,
                "databases": {"tasks": "db-test"},
            },
            "mode": {"skip_time": skip_time},
        },
        notion_token="test",
        tz="Asia/Ho_Chi_Minh",
    )


def task_page(
    *,
    id_="page-1",
    name="Test task",
    time_mark="2026-06-01T09:00:00+07:00",
    deadline=None,
    is_done=False,
    repeat="once",
    remind=False,
    end_time=None,
):
    deadline_prop = {"type": "date", "date": {"start": deadline, "end": None}} if deadline else {
        "type": "date",
        "date": None,
    }
    do_on_date = {"start": time_mark, "end": end_time}
    return {
        "id": id_,
        "properties": {
            "What to do": {"type": "title", "title": [{"plain_text": name}]},
            "Do on": {"type": "date", "date": do_on_date},
            "Deadline": deadline_prop,
            "Done?": {"type": "checkbox", "checkbox": is_done},
            "Repeat": {"type": "select", "select": {"name": repeat}},
            "Remind": {"type": "checkbox", "checkbox": remind},
        },
    }


@pytest.fixture
def now():
    return datetime(2026, 6, 1, 10, 0, tzinfo=TZ)


def test_recurring_done_task_gets_updated(now):
    client = MagicMock()
    client.retrieve_pages.return_value = [
        task_page(
            id_="recur-1",
            time_mark="2026-05-30T09:00:00+07:00",
            is_done=True,
            repeat="daily",
        )
    ]
    polling = TaskPolling(make_settings(), client, now=now)
    counts = polling.execute()

    assert counts["recurring_updated"] == 1
    client.update_page.assert_called_once()
    page_id, payload = client.update_page.call_args.args
    assert page_id == "recur-1"
    assert payload["Done?"]["checkbox"] is False
    # date advanced past today's date.
    new_start = payload["Do on"]["date"]["start"]
    assert new_start.startswith("2026-06-01") or new_start >= "2026-06-01"


def test_recurring_skipped_when_end_time_passed(now):
    client = MagicMock()
    client.retrieve_pages.return_value = [
        task_page(
            id_="recur-2",
            time_mark="2026-05-30T09:00:00+07:00",
            end_time="2026-05-31T09:00:00+07:00",
            is_done=True,
            repeat="daily",
        )
    ]
    counts = TaskPolling(make_settings(), client, now=now).execute()
    assert counts["recurring_updated"] == 0
    client.update_page.assert_not_called()


def test_deadline_comment_posted_for_overdue(now):
    client = MagicMock()
    client.retrieve_pages.return_value = [
        task_page(
            id_="late-1",
            name="Pay bill",
            time_mark="2026-05-15T09:00:00+07:00",
            deadline="2026-05-20T09:00:00+07:00",
            is_done=False,
            repeat="once",
        )
    ]
    counts = TaskPolling(make_settings(), client, now=now).execute()
    assert counts["deadline_comment"] == 1
    client.add_comment.assert_called_once()
    _, message = client.add_comment.call_args.args
    assert "Pay bill" in message
    assert "over deadline" in message


def test_deadline_comment_not_posted_when_future(now):
    client = MagicMock()
    client.retrieve_pages.return_value = [
        task_page(
            id_="future-1",
            deadline="2026-12-31T09:00:00+07:00",
            is_done=False,
        )
    ]
    counts = TaskPolling(make_settings(), client, now=now).execute()
    assert counts["deadline_comment"] == 0


def test_reminder_comment_within_15_minutes(now):
    soon = (now + timedelta(minutes=10)).isoformat()
    client = MagicMock()
    client.retrieve_pages.return_value = [
        task_page(
            id_="remind-1",
            name="Standup",
            time_mark=soon,
            is_done=False,
            remind=True,
        )
    ]
    counts = TaskPolling(make_settings(), client, now=now).execute()
    assert counts["reminder_comment"] == 1
    _, message = client.add_comment.call_args.args
    assert "Standup" in message
    assert "minutes" in message or "minute" in message


def test_reminder_not_posted_when_past_or_far_future(now):
    past = (now - timedelta(minutes=5)).isoformat()
    far = (now + timedelta(hours=2)).isoformat()
    client = MagicMock()
    client.retrieve_pages.return_value = [
        task_page(id_="p", time_mark=past, is_done=False, remind=True),
        task_page(id_="f", time_mark=far, is_done=False, remind=True),
    ]
    counts = TaskPolling(make_settings(), client, now=now).execute()
    assert counts["reminder_comment"] == 0


def test_dry_run_does_not_call_writes(now):
    client = MagicMock()
    client.retrieve_pages.return_value = [
        task_page(
            id_="recur-1",
            time_mark="2026-05-30T09:00:00+07:00",
            is_done=True,
            repeat="daily",
        ),
        task_page(
            id_="late-1",
            deadline="2026-05-01T09:00:00+07:00",
            is_done=False,
        ),
    ]
    counts = TaskPolling(make_settings(), client, dry_run=True, now=now).execute()
    assert counts["recurring_updated"] == 1
    assert counts["deadline_comment"] == 1
    client.update_page.assert_not_called()
    client.add_comment.assert_not_called()
