from __future__ import annotations

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import click

from .config import Settings, load_settings
from .logging import setup_logging
from .notion.client import DatabaseClient
from .notion.task_polling import TaskPolling


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Personal task tracker — polls a Notion database for recurring tasks and reminders."""
    settings = load_settings()
    setup_logging(verbose=verbose, tz=settings.tz)
    ctx.obj = settings


@main.command()
@click.option("--dry-run", is_flag=True, help="Log actions without modifying Notion.")
@click.pass_obj
def poll(settings: Settings, dry_run: bool) -> None:
    """Run one polling cycle (equivalent to the old TaskUpdate Sidekiq job)."""
    log = logging.getLogger("personal_tracker")

    if not settings.notion_token:
        log.error("NOTION_SECRET_TOKEN is not set in environment.")
        sys.exit(1)

    database_id = settings.databases.get("tasks")
    if not database_id:
        log.error("notion.databases.tasks is not configured in settings.")
        sys.exit(1)

    with DatabaseClient(database_id=database_id, token=settings.notion_token) as client:
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


if __name__ == "__main__":
    main()
