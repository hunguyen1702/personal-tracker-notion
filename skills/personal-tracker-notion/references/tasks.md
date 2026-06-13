# Task commands: add / update / find / delete / list-today

All examples assume a global install. From a repo checkout, prepend `uv run`.

## Locating an existing task

`update`, `find`, and `delete` all take **exactly one** of:

- `--id <notion-page-id>` — UUID-style Notion page id. Exact, fastest.
- `--name "<title>"` — exact title match (`title.equals`). Fails with "No task found" if there isn't a perfect match.

Passing both, or neither, raises `UsageError`. Prefer `--id` when you have it.

To get an id, run `find --name "..."` once and read the `id:` line, or `list-today --show-id`. **If you don't know the exact title, use `search` (below) — it does partial, accent-insensitive matching and prints ids.**

## `add` — create a task

```fish
personal-tracker add --name "Review PRs" --time 2026-06-08T09:00 --remind
```

Flags:

| Flag | Required | Notes |
|---|---|---|
| `--name TEXT` | yes | Page title. |
| `--time ISO` | yes | `Do on`. Naive → localized to `settings.tz`; aware respected. |
| `--end-time ISO` |  | Optional end of the time block. |
| `--deadline ISO` |  | Optional deadline (used by `poll` for overdue comments). |
| `--recurring VAL` |  | `Repeat` value. Defaults to `once`. See `references/recurring.md`. |
| `--remind / --no-remind` |  | Default `--no-remind`. Required for reminder comments to fire. |
| `--done / --no-done` |  | Mark already-done on creation (rare). |
| `--dry-run` |  | Print the JSON payload, don't write. |

`--dry-run` output is the literal `properties` object that would be POSTed — useful for diagnosing why a field isn't sticking (e.g. wrong column name in `definition_fields`).

## `update` — partial edit

Only flags you pass are changed. Boolean toggles are tri-state: omit to leave alone, pass `--done` or `--no-done` to set.

```fish
# Mark done by name
personal-tracker update --name "Review PRs" --done

# Reschedule by id, also rename
personal-tracker update --id 1f3b… --time 2026-06-09T10:30 --rename "Review PRs (carry over)"

# Toggle reminder off
personal-tracker update --name "Standup" --no-remind
```

| Flag | Effect |
|---|---|
| `--rename TEXT` | Change `task_name`. |
| `--time ISO` | New `Do on`. |
| `--end-time ISO` | New end time. |
| `--deadline ISO` | New deadline. |
| `--recurring VAL` | New `Repeat`. |
| `--remind / --no-remind` | Set reminder flag explicitly. |
| `--done / --no-done` | Set done flag explicitly. |
| `--dry-run` | Print `{page_id, properties}` instead of writing. |

Tip: `update` round-trips the rest of the task verbatim, so unrelated fields are preserved.

## `find` — read

```fish
personal-tracker find --name "Standup"
personal-tracker find --id 1f3b...
```

Prints a fixed multi-line block:

```
id:        <uuid>
name:      Standup
time_mark: 2026-06-08T09:00:00+07:00
end_time:  -
deadline:  -
recurring: weekday
remind:    True
is_done:   False
```

`-` means the field is unset. `time_mark` is normalized to `settings.tz`.

## `search` — partial title lookup

Use this when you don't know the exact title. `find --name` needs a perfect match; `search` does not.

```fish
personal-tracker search --query "review"
personal-tracker search --query "hoc ky thuat" --show-id
```

| Flag | Notes |
|---|---|
| `--query TEXT` | required | Search terms. Split on whitespace; a task matches only if its title contains **every** term. |
| `--show-id` |  | Append the Notion page id to each line — copy it into `find`/`update`/`delete --id`. |

Matching rules:

- **Case- and accent-insensitive.** `hoc ky thuat` matches `Học các kỹ thuật harness`; `Đ`/`đ` fold to `d` (`don gao` matches `Đón Gạo…`).
- **All terms required, order-independent.** Terms need not be contiguous — `học thuật` matches `Học các kỹ thuật` because both words appear. A title missing any term is excluded.
- Output mirrors `list-today` but with a full date prefix, sorted by `Do on`:

```
[ ] 2026-06-13 22:00  Học các kỹ thuật harness  (37d6c30e-…)
[x] 2026-06-12 09:00  Review PRs                (1f3b…)
```

- No match prints `No tasks match '<query>'.` and exits 0.
- An empty/whitespace-only `--query` returns nothing and makes **no** API call.

Note: `search` fetches the full task list and filters locally (Notion's server-side filter can't ignore accents), so it reads the whole database each call — fine for a personal tracker, but it's not a server-side query like `list-today`.

## `delete` — archive (soft-delete)

```fish
personal-tracker delete --name "Old task"          # interactive confirm
personal-tracker delete --id 1f3b… --yes           # no prompt
personal-tracker delete --name "Old task" --dry-run # resolve only
```

- Calls `PATCH /pages/{id}` with `{"archived": true}`. **Not reversible via this CLI** — undo it in the Notion UI.
- The task block is printed first, then the prompt. `--yes` skips the prompt.
- `--dry-run` resolves and prints the task and exits; nothing is archived.

## `list-today`

```fish
personal-tracker list-today
personal-tracker list-today --show-id
personal-tracker list-today --dry-run     # print the Notion filter JSON and exit
```

Lists tasks whose `Do on` falls within today (in `settings.tz`), sorted by time:

```
[ ] 09:00  Review PRs
[x] 10:30  Standup
[ ] --:--  Untimed errand
```

`--:--` appears when `time_mark` is missing or the task has only a date (skip_time mode). `[x]` = done.

## Common recipes

```fish
# "Add a reminder for tomorrow 9am"
personal-tracker add --name "Call dentist" --time 2026-06-08T09:00 --remind

# "Push back the standup by 30 min"
personal-tracker update --name "Standup" --time 2026-06-08T09:30

# "Make this weekly on Tue/Thu"
personal-tracker update --name "Gym" --recurring tue-thu

# "Find that task about kỹ thuật — I forget the exact name"
personal-tracker search --query "ky thuat" --show-id

# "Show me what's on today, with ids so I can edit them"
personal-tracker list-today --show-id

# "Did Notion actually accept the recurring change?"
personal-tracker find --name "Gym"
```
