from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from importlib import resources
from pathlib import Path
from zoneinfo import ZoneInfo

import click
from dateutil.parser import isoparse

from .config import (
    LOCAL_SETTINGS_FILENAME,
    SETTINGS_FILENAME,
    Settings,
    load_settings,
    resolve_config_dir,
)
from .logging import setup_logging
from .notion.client import DatabaseClient
from .notion.models import Task
from .notion.task_polling import TaskPolling
from .notion.task_queries import find_task_by_name, today_filter

ENV_TEMPLATE = """\
# Personal Tracker credentials. Filled by `personal-tracker init`.
NOTION_SECRET_TOKEN=
# TZ=Asia/Ho_Chi_Minh
"""


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Personal task tracker — polls a Notion database for recurring tasks and reminders."""
    settings = load_settings()
    setup_logging(verbose=verbose, tz=settings.tz)
    ctx.obj = settings


def _require_client(settings: Settings) -> tuple[str, str]:
    log = logging.getLogger("personal_tracker")
    if not settings.notion_token:
        log.error("NOTION_SECRET_TOKEN is not set in environment.")
        sys.exit(1)
    database_id = settings.databases.get("tasks")
    if not database_id:
        log.error("notion.databases.tasks is not configured in settings.")
        sys.exit(1)
    return database_id, settings.notion_token


def _parse_datetime(value: str, tz: ZoneInfo) -> datetime:
    dt = isoparse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt


def _lookup_task(
    client: DatabaseClient,
    fields: dict[str, str],
    *,
    page_id: str | None,
    lookup_name: str | None,
) -> Task:
    log = logging.getLogger("personal_tracker")
    if page_id:
        raw_page = client.retrieve_page(page_id)
        result = Task.from_data(raw_page, fields)
        return result if isinstance(result, Task) else result[0]
    assert lookup_name is not None
    found = find_task_by_name(client, fields, lookup_name)
    if found is None:
        log.error("No task found with name %r", lookup_name)
        sys.exit(1)
    return found


def _format_task(task: Task, tz: ZoneInfo) -> str:
    def _fmt(dt: datetime | None) -> str:
        if dt is None:
            return "-"
        local = dt if dt.tzinfo else dt.replace(tzinfo=tz)
        return local.astimezone(tz).isoformat(timespec="seconds")

    return (
        f"id:        {task.notion_object_id}\n"
        f"name:      {task.task_name or '(untitled)'}\n"
        f"time_mark: {_fmt(task.time_mark)}\n"
        f"end_time:  {_fmt(task.end_time)}\n"
        f"deadline:  {_fmt(task.deadline)}\n"
        f"recurring: {task.recurring_type}\n"
        f"remind:    {task.remind}\n"
        f"is_done:   {task.is_done}"
    )


@main.command()
@click.option("--dry-run", is_flag=True, help="Log actions without modifying Notion.")
@click.pass_obj
def poll(settings: Settings, dry_run: bool) -> None:
    """Run one polling cycle (equivalent to the old TaskUpdate Sidekiq job)."""
    log = logging.getLogger("personal_tracker")
    database_id, token = _require_client(settings)

    with DatabaseClient(database_id=database_id, token=token) as client:
        polling = TaskPolling(settings=settings, client=client, dry_run=dry_run)
        counts = polling.execute()

    tz = ZoneInfo(settings.tz)
    log.info(
        "[%s] Tasks list have been updated (recurring=%d, deadline=%d, reminder=%d, dry_run=%s)",
        datetime.now(tz=tz).isoformat(timespec="seconds"),
        counts["recurring_updated"],
        counts["deadline_comment"],
        counts["reminder_comment"],
        dry_run,
    )


@main.command()
@click.option("--name", required=True, help="Task name (title).")
@click.option("--time", "time_", required=True, help="Do-on datetime (ISO 8601).")
@click.option("--end-time", default=None, help="Optional end datetime (ISO 8601).")
@click.option("--deadline", default=None, help="Optional deadline (ISO 8601).")
@click.option("--recurring", default="once", show_default=True, help="Repeat type.")
@click.option("--remind/--no-remind", default=False, help="Send reminder before time_mark.")
@click.option("--done/--no-done", default=False, help="Mark task as done on creation.")
@click.option("--dry-run", is_flag=True, help="Print payload without creating.")
@click.pass_obj
def add(
    settings: Settings,
    name: str,
    time_: str,
    end_time: str | None,
    deadline: str | None,
    recurring: str,
    remind: bool,
    done: bool,
    dry_run: bool,
) -> None:
    """Create a new task in the Notion database."""
    log = logging.getLogger("personal_tracker")
    database_id, token = _require_client(settings)
    tz = ZoneInfo(settings.tz)

    task = Task(
        notion_object_id="",
        task_name=name,
        time_mark=_parse_datetime(time_, tz),
        end_time=_parse_datetime(end_time, tz) if end_time else None,
        deadline=_parse_datetime(deadline, tz) if deadline else None,
        is_done=done,
        remind=remind,
        recurring_type=recurring,
    )
    payload = task.to_data(
        settings.definition_fields,
        skip_time=settings.skip_time,
        tz=tz,
    )

    if dry_run:
        click.echo(json.dumps({"properties": payload}, indent=2, default=str))
        return

    with DatabaseClient(database_id=database_id, token=token) as client:
        page = client.create_page(payload)
    log.info("Created task %s (id=%s)", name, page.get("id"))


@main.command()
@click.option("--id", "page_id", default=None, help="Notion page id of the task.")
@click.option("--name", "lookup_name", default=None, help="Exact task name to look up.")
@click.option("--rename", default=None, help="New task name.")
@click.option("--time", "time_", default=None, help="New Do-on datetime (ISO 8601).")
@click.option("--end-time", default=None, help="New end datetime (ISO 8601).")
@click.option("--deadline", default=None, help="New deadline (ISO 8601).")
@click.option("--recurring", default=None, help="New Repeat value.")
@click.option(
    "--remind/--no-remind",
    "remind",
    default=None,
    help="Toggle reminder flag.",
)
@click.option("--done/--no-done", "done", default=None, help="Toggle done flag.")
@click.option("--dry-run", is_flag=True, help="Print payload without updating.")
@click.pass_obj
def update(
    settings: Settings,
    page_id: str | None,
    lookup_name: str | None,
    rename: str | None,
    time_: str | None,
    end_time: str | None,
    deadline: str | None,
    recurring: str | None,
    remind: bool | None,
    done: bool | None,
    dry_run: bool,
) -> None:
    """Update an existing task — locate it by --id or --name."""
    log = logging.getLogger("personal_tracker")
    if bool(page_id) == bool(lookup_name):
        raise click.UsageError("Provide exactly one of --id or --name.")

    database_id, token = _require_client(settings)
    tz = ZoneInfo(settings.tz)
    fields = settings.definition_fields

    with DatabaseClient(database_id=database_id, token=token) as client:
        task = _lookup_task(client, fields, page_id=page_id, lookup_name=lookup_name)

        if rename is not None:
            task.task_name = rename
        if time_ is not None:
            task.time_mark = _parse_datetime(time_, tz)
        if end_time is not None:
            task.end_time = _parse_datetime(end_time, tz)
        if deadline is not None:
            task.deadline = _parse_datetime(deadline, tz)
        if recurring is not None:
            task.recurring_type = recurring
        if remind is not None:
            task.remind = remind
        if done is not None:
            task.is_done = done

        payload = task.to_data(fields, skip_time=settings.skip_time, tz=tz)

        if dry_run:
            click.echo(
                json.dumps(
                    {"page_id": task.notion_object_id, "properties": payload},
                    indent=2,
                    default=str,
                )
            )
            return

        client.update_page(task.notion_object_id, payload)
    log.info("Updated task %s (id=%s)", task.task_name, task.notion_object_id)


@main.command()
@click.option("--id", "page_id", default=None, help="Notion page id of the task.")
@click.option("--name", "lookup_name", default=None, help="Exact task name to look up.")
@click.pass_obj
def find(settings: Settings, page_id: str | None, lookup_name: str | None) -> None:
    """Look up a task by --id or --name and print its details."""
    if bool(page_id) == bool(lookup_name):
        raise click.UsageError("Provide exactly one of --id or --name.")

    database_id, token = _require_client(settings)
    tz = ZoneInfo(settings.tz)
    fields = settings.definition_fields

    with DatabaseClient(database_id=database_id, token=token) as client:
        task = _lookup_task(client, fields, page_id=page_id, lookup_name=lookup_name)
    click.echo(_format_task(task, tz))


@main.command()
@click.option("--id", "page_id", default=None, help="Notion page id of the task.")
@click.option("--name", "lookup_name", default=None, help="Exact task name to look up.")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@click.option("--dry-run", is_flag=True, help="Resolve the task without archiving.")
@click.pass_obj
def delete(
    settings: Settings,
    page_id: str | None,
    lookup_name: str | None,
    yes: bool,
    dry_run: bool,
) -> None:
    """Archive a task (Notion soft-delete) by --id or --name."""
    log = logging.getLogger("personal_tracker")
    if bool(page_id) == bool(lookup_name):
        raise click.UsageError("Provide exactly one of --id or --name.")

    database_id, token = _require_client(settings)
    tz = ZoneInfo(settings.tz)
    fields = settings.definition_fields

    with DatabaseClient(database_id=database_id, token=token) as client:
        task = _lookup_task(client, fields, page_id=page_id, lookup_name=lookup_name)
        click.echo(_format_task(task, tz))

        if dry_run:
            click.echo("(dry-run) would archive this task.")
            return

        if not yes and not click.confirm("Archive this task?", default=False):
            click.echo("Aborted.")
            return

        client.archive_page(task.notion_object_id)
    log.info("Archived task %s (id=%s)", task.task_name, task.notion_object_id)


@main.command("list-today")
@click.option("--show-id", is_flag=True, help="Include Notion page id in output.")
@click.option("--dry-run", is_flag=True, help="Print the Notion filter and exit.")
@click.pass_obj
def list_today(settings: Settings, show_id: bool, dry_run: bool) -> None:
    """List tasks whose Do-on date is today."""
    database_id, token = _require_client(settings)
    tz = ZoneInfo(settings.tz)
    fields = settings.definition_fields
    now = datetime.now(tz=tz)
    notion_filter = today_filter(fields, now=now, tz=tz)

    if dry_run:
        click.echo(json.dumps(notion_filter, indent=2))
        return

    with DatabaseClient(database_id=database_id, token=token) as client:
        raw_pages = client.retrieve_pages(filter=notion_filter)

    result = Task.from_data(raw_pages, fields)
    tasks: list[Task] = result if isinstance(result, list) else [result]
    def _sort_key(t: Task) -> datetime:
        tm = t.time_mark or datetime.max
        return tm if tm.tzinfo else tm.replace(tzinfo=tz)

    tasks.sort(key=_sort_key)

    if not tasks:
        click.echo("No tasks scheduled for today.")
        return

    for task in tasks:
        status = "[x]" if task.is_done else "[ ]"
        when = task.time_mark.astimezone(tz).strftime("%H:%M") if task.time_mark else "--:--"
        line = f"{status} {when}  {task.task_name or '(untitled)'}"
        if show_id:
            line += f"  ({task.notion_object_id})"
        click.echo(line)


@main.command()
@click.option(
    "--config-dir",
    "config_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Directory to write settings into. Defaults to the resolver order documented in README.",
)
@click.option("--force", is_flag=True, help="Overwrite existing settings.yml / .env.")
def init(config_dir: Path | None, force: bool) -> None:
    """Scaffold settings.yml + .env into the user config directory."""
    target = (config_dir or resolve_config_dir()).expanduser()
    target.mkdir(parents=True, exist_ok=True)

    defaults_text = (
        resources.files("personal_tracker._defaults")
        .joinpath(SETTINGS_FILENAME)
        .read_text(encoding="utf-8")
    )

    written: list[Path] = []
    skipped: list[Path] = []
    for name, content in (
        (SETTINGS_FILENAME, defaults_text),
        (".env", ENV_TEMPLATE),
    ):
        path = target / name
        if path.exists() and not force:
            skipped.append(path)
            continue
        path.write_text(content, encoding="utf-8")
        written.append(path)

    for path in written:
        click.echo(f"wrote   {path}")
    for path in skipped:
        click.echo(f"exists  {path} (use --force to overwrite)")

    local_path = target / LOCAL_SETTINGS_FILENAME
    if not local_path.exists():
        click.echo(
            f"hint    create {local_path} to override per-machine settings "
            "(e.g. notion.databases.tasks)."
        )

    click.echo("")
    click.echo("Next steps:")
    click.echo(f"  1. Put your Notion integration token in {target / '.env'}")
    click.echo(
        f"  2. Set notion.databases.tasks (your DB id) in {target / SETTINGS_FILENAME} "
        f"or {local_path}"
    )
    click.echo("  3. Run: personal-tracker poll --dry-run")


if __name__ == "__main__":
    main()
