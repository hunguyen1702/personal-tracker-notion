# personal-tracker-notion

Python CLI that polls a Notion task database and handles three things on each run:

1. Advances recurring tasks that have been marked done (resets `Done?` and bumps `Do on`)
2. Posts a comment on tasks whose `Deadline` has passed but are not done
3. Posts a comment on tasks with `Remind = true` whose `Do on` is within the next 15 minutes

This used to be a Rails + Sidekiq app; it now runs as a single `personal-tracker poll` invocation scheduled by your OS cron.

The last Ruby version is preserved at git tag `ruby-legacy-final`.

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (package manager)

## Setup

```fish
uv sync                              # creates .venv and installs deps
cp .env.sample .env                  # then edit NOTION_SECRET_TOKEN
cp config/settings.yml config/settings.local.yml  # then edit databases.tasks
```

`config/settings.local.yml` overrides `config/settings.yml` via deep merge. Put the production database id and any local mode flags there.

## Run

```fish
uv run personal-tracker --help
uv run personal-tracker poll --dry-run     # logs intended actions, makes no API writes
uv run personal-tracker poll               # the real thing
uv run personal-tracker -v poll            # debug logging
```

## Schedule via cron

To preserve the old `0 2 * * *` schedule:

```cron
0 2 * * * cd /path/to/personal-tracker-notion && /Users/you/.local/bin/uv run personal-tracker poll >> /var/log/personal-tracker.log 2>&1
```

Replace the `uv` path with `which uv` output from your environment. Cron runs with a minimal `PATH`, so use the absolute path.

## Tests

```fish
uv run pytest -q
uv run pytest --cov=personal_tracker --cov-report=term-missing
uv run ruff check src tests
```

## Configuration reference

`config/settings.yml`:

```yaml
notion:
  definition_fields:
    deadline: "Deadline"
    end_time: "Do on end"
    is_done: "Done?"
    recurring_type: "Repeat"
    task_name: "What to do"
    time_mark: "Do on"
    remind: "Remind"
  databases:
    tasks: "<notion database id>"
mode:
  skip_time: false   # if true, only send YYYY-MM-DD to Notion (ignore time-of-day)
```

Environment variables (from `.env`):

- `NOTION_SECRET_TOKEN` — Notion integration token (required)
- `TZ` — IANA timezone, defaults to `Asia/Ho_Chi_Minh`

## Supported `Repeat` values

`once`, `daily`, `weekly`, `monthly`, `bi-daily`, `bi-daily-on-weekday`, `bi-weekly`, `bi-monthly`, `annually`, `yearly`, `weekday`, `weekend`, `every N days` (1-9), or a hyphen-separated list of weekday abbreviations like `mon-wed-fri`, `tue-thu`, etc.
