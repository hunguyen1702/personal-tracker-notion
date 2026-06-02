from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import Settings
from .client import DatabaseClient
from .models import Task

log = logging.getLogger("personal_tracker.notion.task_polling")

DEADLINE_COMMENT_MESSAGE = "Task `%s` is over deadline!!!"
REMINDER_WINDOW = timedelta(minutes=15)


def _humanize_delta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return "less than a minute"
    minutes = total_seconds // 60
    if minutes == 1:
        return "1 minute"
    return f"{minutes} minutes"


class TaskPolling:
    def __init__(
        self,
        settings: Settings,
        client: DatabaseClient,
        *,
        dry_run: bool = False,
        now: datetime | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.dry_run = dry_run
        self.tz = ZoneInfo(settings.tz)
        self._frozen_now = now

    @property
    def now(self) -> datetime:
        return self._frozen_now if self._frozen_now else datetime.now(tz=self.tz)

    def execute(self) -> dict[str, int]:
        fields = self.settings.definition_fields
        notion_filter = self._build_filter(fields)

        raw_pages = self.client.retrieve_pages(filter=notion_filter)
        result = Task.from_data(raw_pages, fields)
        tasks: list[Task] = result if isinstance(result, list) else [result]
        log.info("Fetched %d task(s) from Notion", len(tasks))

        counts = {"recurring_updated": 0, "deadline_comment": 0, "reminder_comment": 0}

        for task in tasks:
            if self._update_recurring_time(task):
                counts["recurring_updated"] += 1
            if self._post_deadline_remind_message(task):
                counts["deadline_comment"] += 1
            if self._post_task_reminder_message(task):
                counts["reminder_comment"] += 1

        return counts

    def _build_filter(self, fields: dict[str, str]) -> dict:
        clauses = [
            {
                "and": [
                    {"property": fields["is_done"], "checkbox": {"equals": True}},
                    {
                        "property": fields["recurring_type"],
                        "select": {"does_not_equal": "once"},
                    },
                ]
            },
            {
                "and": [
                    {"property": fields["is_done"], "checkbox": {"equals": False}},
                    {"property": fields["deadline"], "date": {"is_not_empty": True}},
                ]
            },
        ]
        if "remind" in fields:
            clauses.append(
                {
                    "and": [
                        {"property": fields["is_done"], "checkbox": {"equals": False}},
                        {"property": fields["remind"], "checkbox": {"equals": True}},
                    ]
                }
            )
        return {"or": clauses}

    def _update_recurring_time(self, task: Task) -> bool:
        if not (task.is_done and task.is_valid() and task.recurring_type != "once"):
            return False

        next_time = task.next_time_by_recurring_type(now=self.now)
        if next_time is None:
            log.debug("No next time computed for task %s (%s)", task.task_name, task.recurring_type)
            return False
        if task.end_time is not None and next_time > task.end_time:
            log.debug("Task %s reached end_time, skipping update", task.task_name)
            return False

        task.time_mark = next_time.astimezone(self.tz)
        task.is_done = False

        payload = task.to_data(
            self.settings.definition_fields,
            skip_time=self.settings.skip_time,
            tz=self.tz,
        )
        log.info(
            "Recurring update: %s -> %s", task.task_name, task.time_mark.isoformat()
        )
        if self.dry_run:
            return True
        self.client.update_page(task.notion_object_id, payload)
        return True

    def _post_deadline_remind_message(self, task: Task) -> bool:
        if task.is_done or task.deadline is None:
            return False
        if self.settings.skip_time:
            current = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            current = self.now
        deadline = (
            task.deadline if task.deadline.tzinfo else task.deadline.replace(tzinfo=self.tz)
        )
        if deadline > current:
            return False

        message = DEADLINE_COMMENT_MESSAGE % task.task_name
        log.info("Deadline comment for %s", task.task_name)
        if self.dry_run:
            return True
        self.client.add_comment(task.notion_object_id, message)
        return True

    def _post_task_reminder_message(self, task: Task) -> bool:
        if task.is_done or not task.remind or task.time_mark is None:
            return False

        time_mark = (
            task.time_mark if task.time_mark.tzinfo else task.time_mark.replace(tzinfo=self.tz)
        )
        now = self.now
        if time_mark < now or time_mark > now + REMINDER_WINDOW:
            return False

        delta = time_mark - now
        message = (
            f"Task {task.task_name} is should be started in "
            f"{_humanize_delta(delta)} ({time_mark.astimezone(self.tz).strftime('%H:%M')})"
        )
        log.info("Reminder comment for %s", task.task_name)
        if self.dry_run:
            return True
        self.client.add_comment(task.notion_object_id, message)
        return True
