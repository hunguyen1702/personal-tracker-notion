from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from personal_tracker.notion.models import Task

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

MAPPING = {
    "task_name": "What to do",
    "time_mark": "Do on",
    "end_time": "Do on end",
    "deadline": "Deadline",
    "is_done": "Done?",
    "recurring_type": "Repeat",
    "remind": "Remind",
}


def sample_page():
    return {
        "id": "page-1",
        "properties": {
            "What to do": {"type": "title", "title": [{"plain_text": "Read book"}]},
            "Do on": {"type": "date", "date": {"start": "2026-06-01T09:00:00+07:00", "end": None}},
            "Deadline": {"type": "date", "date": {"start": "2026-06-10", "end": None}},
            "Done?": {"type": "checkbox", "checkbox": False},
            "Repeat": {"type": "select", "select": {"name": "daily"}},
            "Remind": {"type": "checkbox", "checkbox": True},
        },
    }


def test_from_data_single():
    task = Task.from_data(sample_page(), MAPPING)
    assert isinstance(task, Task)
    assert task.notion_object_id == "page-1"
    assert task.task_name == "Read book"
    assert task.recurring_type == "daily"
    assert task.is_done is False
    assert task.remind is True
    assert task.time_mark == datetime(2026, 6, 1, 9, 0, tzinfo=TZ)


def test_from_data_with_date_end():
    page = sample_page()
    page["properties"]["Do on"]["date"]["end"] = "2026-06-05T10:00:00+07:00"
    task = Task.from_data(page, MAPPING)
    assert task.end_time == datetime(2026, 6, 5, 10, 0, tzinfo=TZ)


def test_from_data_list():
    tasks = Task.from_data([sample_page(), sample_page()], MAPPING)
    assert isinstance(tasks, list)
    assert len(tasks) == 2


def test_to_data_round_trip_iso():
    task = Task.from_data(sample_page(), MAPPING)
    task.is_done = True
    task.time_mark = datetime(2026, 6, 2, 9, 0, tzinfo=TZ)
    out = task.to_data(MAPPING, skip_time=False, tz=TZ)
    assert out["Done?"]["checkbox"] is True
    assert out["Do on"]["date"]["start"] == "2026-06-02T09:00:00+07:00"
    assert out["Repeat"]["select"]["name"] == "daily"


def test_to_data_skip_time_drops_clock():
    task = Task.from_data(sample_page(), MAPPING)
    task.time_mark = datetime(2026, 6, 2, 9, 0, tzinfo=TZ)
    out = task.to_data(MAPPING, skip_time=True, tz=TZ)
    assert out["Do on"]["date"]["start"] == "2026-06-02"


def test_is_valid_requires_required_attrs():
    task = Task(notion_object_id="x", task_name=None, time_mark=None)
    assert task.is_valid() is False
    task2 = Task(
        notion_object_id="x",
        task_name="Hi",
        time_mark=datetime(2026, 6, 1, 9, tzinfo=TZ),
        recurring_type="once",
    )
    assert task2.is_valid() is True


@pytest.mark.parametrize("missing_id", [None, ""])
def test_is_valid_requires_notion_id(missing_id):
    task = Task(
        notion_object_id=missing_id,
        task_name="Hi",
        time_mark=datetime(2026, 6, 1, 9, tzinfo=TZ),
    )
    assert task.is_valid() is False
