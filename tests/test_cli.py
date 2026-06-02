from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from personal_tracker.cli import main
from personal_tracker.config import Settings

DEFINITION_FIELDS = {
    "task_name": "What to do",
    "time_mark": "Do on",
    "end_time": "Do on end",
    "deadline": "Deadline",
    "is_done": "Done?",
    "recurring_type": "Repeat",
    "remind": "Remind",
}


def _settings(skip_time: bool = False) -> Settings:
    return Settings(
        data={
            "notion": {
                "definition_fields": DEFINITION_FIELDS,
                "databases": {"tasks": "db-test"},
            },
            "mode": {"skip_time": skip_time},
        },
        notion_token="test-token",
        tz="Asia/Ho_Chi_Minh",
    )


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    return client


def _invoke(runner, mock_client, args, settings=None):
    settings = settings or _settings()
    with patch("personal_tracker.cli.load_settings", return_value=settings), patch(
        "personal_tracker.cli.DatabaseClient", return_value=mock_client
    ):
        return runner.invoke(main, args, catch_exceptions=False)


def test_add_dry_run_prints_payload(runner, mock_client):
    result = _invoke(
        runner,
        mock_client,
        ["add", "--name", "Standup", "--time", "2026-06-02T09:00", "--dry-run"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    props = payload["properties"]
    assert props["What to do"]["title"][0]["plain_text"] == "Standup"
    assert props["Do on"]["date"]["start"].startswith("2026-06-02T09:00:00")
    assert props["Repeat"]["select"]["name"] == "once"
    mock_client.create_page.assert_not_called()


def test_add_creates_page(runner, mock_client):
    mock_client.create_page.return_value = {"id": "new-id"}
    result = _invoke(
        runner,
        mock_client,
        [
            "add",
            "--name",
            "Standup",
            "--time",
            "2026-06-02T09:00",
            "--remind",
            "--deadline",
            "2026-06-05T10:00",
        ],
    )
    assert result.exit_code == 0
    mock_client.create_page.assert_called_once()
    props = mock_client.create_page.call_args.args[0]
    assert props["Remind"]["checkbox"] is True
    assert props["Deadline"]["date"]["start"].startswith("2026-06-05")


def test_update_requires_id_or_name(runner, mock_client):
    result = _invoke(runner, mock_client, ["update", "--rename", "X"])
    assert result.exit_code != 0
    assert "Provide exactly one" in result.output


def test_update_by_id(runner, mock_client):
    mock_client.retrieve_page.return_value = {
        "id": "p-1",
        "properties": {
            "What to do": {"type": "title", "title": [{"plain_text": "Old"}]},
            "Do on": {"type": "date", "date": {"start": "2026-06-01T09:00:00+07:00", "end": None}},
            "Done?": {"type": "checkbox", "checkbox": False},
            "Repeat": {"type": "select", "select": {"name": "once"}},
            "Remind": {"type": "checkbox", "checkbox": False},
        },
    }
    result = _invoke(
        runner,
        mock_client,
        ["update", "--id", "p-1", "--done", "--rename", "Renamed"],
    )
    assert result.exit_code == 0, result.output
    mock_client.update_page.assert_called_once()
    page_id, props = mock_client.update_page.call_args.args
    assert page_id == "p-1"
    assert props["Done?"]["checkbox"] is True
    assert props["What to do"]["title"][0]["plain_text"] == "Renamed"


def test_list_today_dry_run_prints_filter(runner, mock_client):
    result = _invoke(runner, mock_client, ["list-today", "--dry-run"])
    assert result.exit_code == 0
    filt = json.loads(result.output)
    assert filt["property"] == "Do on"
    assert "equals" in filt["date"]


def test_list_today_prints_tasks(runner, mock_client):
    mock_client.retrieve_pages.return_value = [
        {
            "id": "p-1",
            "properties": {
                "What to do": {"type": "title", "title": [{"plain_text": "Eat"}]},
                "Do on": {
                    "type": "date",
                    "date": {"start": "2026-06-02T08:00:00+07:00", "end": None},
                },
                "Done?": {"type": "checkbox", "checkbox": False},
                "Repeat": {"type": "select", "select": {"name": "once"}},
                "Remind": {"type": "checkbox", "checkbox": False},
            },
        },
        {
            "id": "p-2",
            "properties": {
                "What to do": {"type": "title", "title": [{"plain_text": "Sleep"}]},
                "Do on": {
                    "type": "date",
                    "date": {"start": "2026-06-02T22:00:00+07:00", "end": None},
                },
                "Done?": {"type": "checkbox", "checkbox": True},
                "Repeat": {"type": "select", "select": {"name": "once"}},
                "Remind": {"type": "checkbox", "checkbox": False},
            },
        },
    ]
    result = _invoke(runner, mock_client, ["list-today"])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert lines[0].startswith("[ ] 08:00")
    assert "Eat" in lines[0]
    assert lines[1].startswith("[x] 22:00")
    assert "Sleep" in lines[1]


def test_list_today_empty(runner, mock_client):
    mock_client.retrieve_pages.return_value = []
    result = _invoke(runner, mock_client, ["list-today"])
    assert result.exit_code == 0
    assert "No tasks" in result.output
