---
name: personal-tracker-notion
description: How to use the `personal-tracker` CLI — a Python tool that syncs a Notion task database (recurring tasks, deadline comments, reminders) and exposes commands to add/update/find/search/delete/list tasks. Use this skill whenever the user mentions `personal-tracker`, wants to manage tasks in their Notion task database from the terminal, asks about adding/updating/finding/searching tasks via CLI, wants to schedule the poller via cron, asks about the `Repeat`/recurring values supported, or needs to install or configure the tool — even if they don't name the CLI explicitly (e.g. "add a task to my tracker", "search for a task by keyword", "remind me tomorrow via Notion", "list today's tasks").
---

# personal-tracker CLI

`personal-tracker` is a Click-based Python CLI that talks to a Notion database of tasks. One process = one action. It is designed to be either driven by a human (`add`, `update`, `find`, `delete`, `list-today`) or scheduled by cron (`poll`).

The user invokes it as `personal-tracker <command>` after a global install (e.g. `uv tool install …`), or as `uv run personal-tracker <command>` from inside the repo checkout. Pick whichever form matches the user's environment — don't switch them.

## Command map

| Command | Purpose |
|---|---|
| `init` | Scaffold `settings.yml` + `.env` into the user config dir. First-run setup. |
| `poll` | Run one polling cycle: advance recurring done-tasks, post deadline + reminder comments. |
| `add` | Create a task. Requires `--name` and `--time`. |
| `update` | Modify a task by `--id` XOR `--name`. Only the flags passed are changed. |
| `find` | Print a task's fields, located by `--id` XOR `--name`. |
| `search` | List tasks by partial title match (`--query`), case- and accent-insensitive. Use when the exact name is unknown. |
| `delete` | Archive (soft-delete) a task. Prompts unless `--yes`. |
| `list-today` | Print tasks whose `Do on` is today, sorted by time. |

Every mutating command (`add`, `update`, `delete`, `poll`) supports `--dry-run` — use it whenever the user is exploring or unsure. It prints the would-be payload / Notion filter and exits without writing.

Global flags:
- `-v` / `--verbose` (before the subcommand) — debug logging.
- `--help` works at both the group and subcommand level.

## When to read which reference

Don't load everything. Pick the file that matches the user's task:

- **Installing, first-time setup, config files, env vars, where settings live** → `references/setup.md`
- **Creating, editing, finding, deleting, or listing individual tasks** → `references/tasks.md`
- **Running `poll`, dry-run, scheduling via cron, how the three poll behaviors work** → `references/poll.md`
- **What values `--recurring` / `Repeat` accept** (`weekly`, `mon-wed-fri`, `every N days`, …) → `references/recurring.md`
- **The shape of `settings.yml`, definition_fields mapping, skip_time, timezone** → `references/config.md`

## Hard rules to respect

- **`update`, `find`, `delete` require exactly one of `--id` or `--name`.** Passing both, or neither, raises a `UsageError`. If the user has the page id, prefer it (an exact match); `--name` does a `title.equals` lookup and fails if there's no exact-name match.
- **When the exact title is unknown, use `search --query` first.** It does a partial, case- and accent-insensitive title match (so `hoc ky thuat` finds `Học các kỹ thuật`) and prints every match. Then feed the resulting id into `find`/`update`/`delete --id`. Don't guess at `--name` exact strings.
- **Datetimes are ISO 8601.** Naive values (`2026-06-08T09:00`) are localized to `settings.tz` (default `Asia/Ho_Chi_Minh`); aware values (`2026-06-08T09:00+07:00`) are respected as-is. When in doubt, suggest aware ISO strings.
- **`mode.skip_time: true` drops the time-of-day.** Only `YYYY-MM-DD` is sent to Notion. Reminders within a 15-minute window still depend on a time, so don't enable `skip_time` if reminders matter.
- **Notion has no hard delete via the API.** `delete` calls `PATCH /pages/{id}` with `archived: true`. Archived pages stop appearing in queries but `find --id` can still retrieve them.
- **`NOTION_SECRET_TOKEN` and `notion.databases.tasks` are mandatory.** Without either, every command except `init` exits with code 1 and a clear log line.

## Quick decision tree

1. User has never run it on this machine → walk them through `setup.md` (`init`, fill `.env`, set `databases.tasks`, then `poll --dry-run`).
2. User wants to do something to "the task called X" or "my 9am meeting" → `tasks.md`.
3. User wants this to "run every day" / "fire at 2am" / "stop forgetting" → `poll.md` (poll semantics + cron).
4. User asks "can it repeat every Tuesday and Thursday?" → `recurring.md`.
5. User asks "where do I change the column names / timezone / database id?" → `config.md`.

Default to `--dry-run` the first time you propose any mutating command in a session — let the user see the payload before you commit.
