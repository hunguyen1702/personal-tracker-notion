# `poll` and scheduling

`poll` is the unattended command. One invocation runs all three behaviors against the tasks database and exits. It is the replacement for the old Rails + Sidekiq `TaskUpdate` job — designed to be driven by `cron`, not by a human.

## What it does

In one cycle, in order:

1. **Recurring advance.** For tasks where `Done? = true` and `Repeat != once`, compute the next `Do on` from the current `time_mark` using the `Repeat` rule, set `Done? = false`, and write back. The advance loops forward until the result is on or after `now`, so a task completed late still lands in the future.
2. **Deadline comment.** For tasks where `Deadline < now` and `Done? = false`, post a Notion comment flagging it as overdue.
3. **Reminder comment.** For tasks with `Remind = true` whose `Do on` is within the next 15 minutes (`REMINDER_WINDOW`), post a reminder comment.

The reminder check is only included in the Notion filter if `remind` is declared under `notion.definition_fields` in settings.

## Running it

```fish
personal-tracker poll --dry-run     # log intended actions; no API writes
personal-tracker poll                # the real thing
personal-tracker -v poll             # debug logging (request URLs, payloads)
```

Final log line summarizes counts:

```
[2026-06-07T02:00:13+07:00] Tasks list have been updated (recurring=2, deadline=1, reminder=0, dry_run=False)
```

Exit code is 0 on success even if zero actions occurred. Non-zero means setup error (missing token / DB id) or unhandled API failure.

## Tunables (source-level, not env)

- `REMINDER_WINDOW = timedelta(minutes=15)` in `src/personal_tracker/notion/task_polling.py`.
- `DEFAULT_SLEEP_TIME = 5`, `DEFAULT_MAX_RETRIES = 20` in `src/personal_tracker/notion/client.py` — retry policy on `429` and `5xx`.

These are intentionally constants. Edit the source if you need different values. The reminder cadence and your cron cadence interact — see below.

## Cron — picking a cadence

The old Rails schedule was `0 2 * * *` (daily at 2am). That's fine for recurring advance + overdue comments, but useless for the 15-minute reminder window. Pick based on which behaviors the user cares about:

| Need | Suggested cron |
|---|---|
| Recurring advance + overdue only | `0 2 * * *` (daily) |
| Reminders too | `*/10 * * * *` or `*/5 * * * *` |

Run more often than `REMINDER_WINDOW` (15 min) or reminders will be missed. `*/10` is the safe default if reminders matter; `*/5` if precision matters more than API call budget.

## Cron entry template

```cron
*/10 * * * * cd /path/to/personal-tracker-notion && /Users/you/.local/bin/uv run personal-tracker poll >> /var/log/personal-tracker.log 2>&1
```

Notes:

- Cron's `PATH` is minimal. Use `which uv` (or `which personal-tracker` for the global install) and hard-code the absolute path.
- `cd` only matters in dev mode (so `./config/` resolves). For a `uv tool install` setup that reads from `~/.config/personal-tracker/`, you can drop the `cd`.
- Redirect both streams to a log file. The CLI logs to stderr by default.
- For launchd on macOS (instead of cron), wrap the same command in a `.plist` with `StartInterval = 600`.

## Dry-run workflow

When in doubt:

```fish
personal-tracker poll --dry-run
```

The output is the same log line you'd see in production, with `dry_run=True` and no Notion writes. Use it after editing `settings.yml`, after changing the cron user, or as a smoke test from a new machine.
