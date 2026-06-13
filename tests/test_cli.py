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
    assert "and" in filt
    clauses = filt["and"]
    assert {c["property"] for c in clauses} == {"Do on"}
    ops = {frozenset(c["date"]) for c in clauses}
    assert ops == {frozenset({"on_or_after"}), frozenset({"on_or_before"})}


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


def test_init_scaffolds_files(runner, tmp_path):
    target = tmp_path / "cfg"
    result = runner.invoke(main, ["init", "--config-dir", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "settings.yml").exists()
    assert (target / ".env").exists()
    assert "NOTION_SECRET_TOKEN=" in (target / ".env").read_text()
    assert "What to do" in (target / "settings.yml").read_text()


def test_init_does_not_overwrite_without_force(runner, tmp_path):
    target = tmp_path / "cfg"
    target.mkdir()
    (target / "settings.yml").write_text("preserved: true\n")
    (target / ".env").write_text("NOTION_SECRET_TOKEN=existing\n")

    result = runner.invoke(main, ["init", "--config-dir", str(target)])
    assert result.exit_code == 0
    assert (target / "settings.yml").read_text() == "preserved: true\n"
    assert "existing" in (target / ".env").read_text()
    assert "exists" in result.output


def test_init_force_overwrites(runner, tmp_path):
    target = tmp_path / "cfg"
    target.mkdir()
    (target / "settings.yml").write_text("preserved: true\n")

    result = runner.invoke(main, ["init", "--config-dir", str(target), "--force"])
    assert result.exit_code == 0
    assert "What to do" in (target / "settings.yml").read_text()


def test_add_with_icon_dry_run(runner, mock_client):
    result = _invoke(
        runner,
        mock_client,
        [
            "add",
            "--name",
            "Standup",
            "--time",
            "2026-06-02T09:00",
            "--icon",
            "🎯",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["icon"] == {"type": "emoji", "emoji": "🎯"}


def test_add_with_content_dry_run(runner, mock_client):
    result = _invoke(
        runner,
        mock_client,
        [
            "add",
            "--name",
            "Standup",
            "--time",
            "2026-06-02T09:00",
            "--content",
            "**bold** note",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["children"] is not None
    assert payload["children"][0]["type"] == "paragraph"
    rt = payload["children"][0]["paragraph"]["rich_text"]
    assert any(frag.get("annotations", {}).get("bold") for frag in rt)


def test_add_with_content_file(runner, mock_client, tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("# Title\n\n- a\n- b\n", encoding="utf-8")
    result = _invoke(
        runner,
        mock_client,
        [
            "add",
            "--name",
            "Standup",
            "--time",
            "2026-06-02T09:00",
            "--content-file",
            str(md),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    types = [b["type"] for b in payload["children"]]
    assert types == ["heading_1", "bulleted_list_item", "bulleted_list_item"]


def test_add_content_and_file_raises(runner, mock_client, tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("hi", encoding="utf-8")
    result = _invoke(
        runner,
        mock_client,
        [
            "add",
            "--name",
            "Standup",
            "--time",
            "2026-06-02T09:00",
            "--content",
            "inline",
            "--content-file",
            str(md),
        ],
    )
    assert result.exit_code != 0
    assert "--content or --content-file" in result.output


def test_add_with_icon_and_content_creates_page(runner, mock_client):
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
            "--icon",
            "🚀",
            "--content",
            "hello",
        ],
    )
    assert result.exit_code == 0, result.output
    mock_client.create_page.assert_called_once()
    call_kwargs = mock_client.create_page.call_args.kwargs
    assert call_kwargs["icon"] == {"type": "emoji", "emoji": "🚀"}
    assert call_kwargs["children"] is not None


def test_update_with_icon_calls_update_page(runner, mock_client):
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
        ["update", "--id", "p-1", "--icon", "🎯"],
    )
    assert result.exit_code == 0, result.output
    mock_client.update_page.assert_called_once()
    icon_kwarg = mock_client.update_page.call_args.kwargs["icon"]
    assert icon_kwarg == {"type": "emoji", "emoji": "🎯"}


def test_update_no_icon_clears(runner, mock_client):
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
        ["update", "--id", "p-1", "--no-icon"],
    )
    assert result.exit_code == 0, result.output
    assert mock_client.update_page.call_args.kwargs["icon"] is None


def test_update_icon_and_no_icon_raises(runner, mock_client):
    result = _invoke(
        runner,
        mock_client,
        ["update", "--id", "p-1", "--icon", "🎯", "--no-icon"],
    )
    assert result.exit_code != 0
    assert "--icon or --no-icon" in result.output


def test_update_content_appends(runner, mock_client):
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
        ["update", "--id", "p-1", "--content", "## Appended"],
    )
    assert result.exit_code == 0, result.output
    mock_client.update_page.assert_called_once()
    update_kwargs = mock_client.update_page.call_args.kwargs
    assert "children" not in update_kwargs
    mock_client.append_block_children.assert_called_once()
    appended = mock_client.append_block_children.call_args.args[1]
    assert appended[0]["type"] == "heading_2"


def test_update_content_file_not_found(runner, mock_client):
    result = _invoke(
        runner,
        mock_client,
        ["update", "--id", "p-1", "--content-file", "/tmp/does-not-exist.md"],
    )
    assert result.exit_code != 0


def test_update_with_icon_dry_run(runner, mock_client):
    result = _invoke(
        runner,
        mock_client,
        ["update", "--id", "p-1", "--icon", "🎯", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["icon"] == {"type": "emoji", "emoji": "🎯"}
