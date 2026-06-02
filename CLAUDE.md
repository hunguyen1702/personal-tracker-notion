# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Python CLI (`personal-tracker poll`) that runs three behaviors against a Notion task database on each invocation. Originally a Rails + Sidekiq app; the legacy Ruby source is preserved at git tag `ruby-legacy-final` and the working tree is fully Python (3.12+, managed by `uv`). Intended to be run on a cron — one poll = one process.

The three polling behaviors (see `notion/task_polling.py:46` `TaskPolling.execute`):

1. **Recurring advance** — for tasks marked done with `Repeat != once`, compute the next `Do on` and reset `Done? = false`.
2. **Deadline comment** — for tasks with a `Deadline` in the past that aren't done, post a comment.
3. **Reminder comment** — for tasks with `Remind = true` and `Do on` within the next 15 minutes (`REMINDER_WINDOW`), post a comment.

## Commands

All run inside the `uv` venv — prepend `uv run` if you haven't activated it.

```fish
uv sync                                            # install deps
uv run personal-tracker poll --dry-run             # see intended actions, no API writes
uv run personal-tracker poll                       # the real run
uv run personal-tracker -v poll                    # debug logging
uv run personal-tracker add --name X --time ISO    # create a task (supports --dry-run)
uv run personal-tracker update --id ID --done      # mutate by --id or --name (XOR)
uv run personal-tracker find --name X              # print task details
uv run personal-tracker delete --name X --yes      # archive (soft-delete)
uv run personal-tracker list-today                 # today's tasks by Do on
uv run pytest -q                                   # full test suite
uv run pytest tests/test_recurring.py -k weekly    # one test by node id
uv run pytest --cov=personal_tracker --cov-report=term-missing
uv run ruff check src tests                        # lint
```

## Architecture

**Entry point** — `src/personal_tracker/cli.py`. A Click group with subcommands `poll`, `add`, `update`, `find`, `delete`, `list-today`. All share `_require_client` (exits 1 if `NOTION_SECRET_TOKEN` or the tasks database id is missing) and use `DatabaseClient` as a context manager. Lookups by `--id` or `--name` go through `_lookup_task` (XOR-validated).

**Config** — `src/personal_tracker/config.py`. Loads `config/settings.yml`, deep-merges `config/settings.local.yml` on top, then layers env vars (`.env` is loaded by `python-dotenv`, not overriding the shell). The `Settings` object exposes `definition_fields` (Notion property name → internal attribute name) and `databases` (logical name → database id). The `mode.skip_time` flag in settings controls whether date-with-time fields are sent as ISO datetimes or just `YYYY-MM-DD`.

**Notion HTTP client** — `src/personal_tracker/notion/client.py`. Thin wrapper over `httpx.Client` with built-in retry/backoff for `429` and `5xx` (default 5 s sleep, 20 attempts). Three operations: `retrieve_pages` (paginated `POST /databases/{id}/query`, strips `formula` properties since they aren't writable), `update_page` (`PATCH /pages/{id}`), `add_comment` (`POST /comments`).

**Task model** — `src/personal_tracker/notion/models.py`. A `@dataclass` that round-trips Notion's nested property JSON. `to_data()` starts from `deepcopy(self.raw_data)`; when `raw_data` is empty (newly-created tasks for `add`) it scaffolds empty property containers from `PROPERTY_TYPES`, then runs the same patch logic — one code path for create and update. `from_data()` handles the inverse for `select`/`date`/`checkbox`/`title`. Date parsing goes through `dateutil.parser.isoparse`.

**Recurring date logic** — `src/personal_tracker/notion/recurring.py`. Pure functions, no Notion coupling. `_next_recurring_time_of` handles one step; the public `next_time_by_recurring_type` loops until the result is on or after `now` (handles the case where a task was completed late). Supports the `Repeat` enum values listed in the README plus hyphen-separated weekday abbreviations (`mon-wed-fri`) and `every N days` for N=1..9. The `every N days` branch adds N+1 days, matching the original Ruby behavior — do not "fix" this to +N.

**Polling orchestrator** — `src/personal_tracker/notion/task_polling.py`. `TaskPolling` accepts a `now` kwarg for time injection (used by tests via `freezegun`). Each behavior method returns `True` if it did (or would have, in dry-run) made a write, so the caller can tally counts. The Notion query filter is built in `_build_filter` as an `or` of three `and` clauses — the third (reminder) is only added if `remind` is configured in `definition_fields`.

## Conventions

- **Notion `select` writes must drop `id`/`color`.** Notion prioritizes the `id` field over `name` on update, so preserving the raw select object causes value changes to silently no-op. `to_data()` writes `{"select": {"name": value}}` only — don't "optimize" this by carrying over `id`.
- **`time_mark` can be tz-naive when `skip_time=true`.** Notion returns date-only strings (e.g. `"2026-06-02"`) for skip-time tasks, which parse to naive `datetime` via `isoparse`. Always normalize to tz-aware before comparing or sorting (see `list_today` in `cli.py`).
- **Notion has no hard delete via API.** `DatabaseClient.archive_page` sends `PATCH /pages/{id}` with `{"archived": true}`. Archived pages disappear from `retrieve_pages` (DB queries) but `retrieve_page` by id still returns them.
- The Notion property names in the database (e.g. `"What to do"`, `"Do on"`) are *not* hardcoded — they're declared in `config/settings.yml` under `notion.definition_fields`. To support a database with different column names, only the YAML needs to change.
- `Task.is_valid()` requires `task_name`, `time_mark`, and `recurring_type` to be non-empty before recurring advance runs; deadline and reminder checks are looser.
- All datetimes flowing into Notion are localized to `settings.tz` (default `Asia/Ho_Chi_Minh`). `to_data()` calls `astimezone(tz)` on every datetime field it writes.
- When `mode.skip_time` is true, the deadline check compares at midnight (a deadline of "today" is treated as overdue all day). When false, a date-only deadline parses as `00:00` of that day, so it counts as overdue the moment that day begins. Same `> current` test, different granularity.
- The reminder window (`REMINDER_WINDOW = timedelta(minutes=15)` in `task_polling.py:14`) and the HTTP retry policy (`DEFAULT_SLEEP_TIME = 5`, `DEFAULT_MAX_RETRIES = 20` in `client.py:11-12`) are module-level constants — not env vars. To change them, edit the source.
- Tests use `pytest-httpx` to mock the Notion API and `freezegun` to pin time. Test files mirror the source layout one-to-one (`test_models.py` ↔ `models.py`, etc.).
- `.env` and `config/settings.local.yml` are gitignored — they're per-machine secrets and overrides, respectively.
