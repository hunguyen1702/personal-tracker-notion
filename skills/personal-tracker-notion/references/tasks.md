# Task commands: add / update / find / delete / list-today

All examples assume a global install. From a repo checkout, prepend `uv run`.

## Locating an existing task

`update`, `find`, and `delete` all take **exactly one** of:

- `--id <notion-page-id>` — UUID-style Notion page id. Exact, fastest.
- `--name "<title>"` — exact title match (`title.equals`). Fails with "No task found" if there isn't a perfect match.

Passing both, or neither, raises `UsageError`. Prefer `--id` when you have it.

To get an id, run `find --name "..."` once and read the `id:` line, or `list-today --show-id`.

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
| `--icon EMOJI` |  | Page emoji icon, e.g. `--icon "🎯"`. |
| `--content MD` |  | Page body as Markdown. Converted to Notion blocks. |
| `--content-file PATH` |  | Read page body Markdown from a file. Mutually exclusive with `--content`. |
| `--dry-run` |  | Print the JSON payload, don't write. |

`--dry-run` output is the JSON the create would POST — `{properties, icon, children}` (the latter two are `null` when not supplied) — useful for diagnosing why a field isn't sticking (e.g. wrong column name in `definition_fields`) or eyeballing the converted blocks.

### Page content & icon

`--content` / `--content-file` take **Markdown** and convert it to Notion blocks. Supported: headings (`#`/`##`/`###`, deeper levels clamp to `heading_3`), paragraphs, bulleted/numbered lists, GFM task lists (`- [ ]` / `- [x]` → Notion to-do), fenced code blocks (with language), block quotes, dividers (`---`), and inline **bold** / *italic* / `code` / [links](url). Images are dropped (Notion needs a separate upload step).

```fish
# Inline markdown body + emoji
personal-tracker add --name "Plan sprint" --time 2026-06-14T09:00 \
  --icon "🎯" --content "## Goals\n- [ ] groom backlog\n- [ ] size stories"

# Body from a file
personal-tracker add --name "Design doc" --time 2026-06-14T09:00 \
  --content-file ./notes.md --dry-run
```

Pass either `--content` or `--content-file`, not both (raises `UsageError`). Empty content adds no blocks.

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
| `--icon EMOJI` | Set the page emoji icon. |
| `--no-icon` | Clear the page icon. Mutually exclusive with `--icon`. |
| `--content MD` | **Append** Markdown body blocks to the page (never replaces existing content). |
| `--content-file PATH` | Append body blocks read from a Markdown file. Mutually exclusive with `--content`. |
| `--dry-run` | Print `{page_id, properties, icon, children}` instead of writing. |

Tip: `update` round-trips the rest of the task verbatim, so unrelated fields are preserved.

Icon is tri-state: omit both flags to leave it untouched, `--icon "✅"` to set, `--no-icon` to clear. Passing both `--icon` and `--no-icon` raises `UsageError`. Content always **appends** — there's no replace; new blocks land at the bottom of the page via `PATCH /blocks/{id}/children`.

```fish
# Swap the icon and append a section
personal-tracker update --name "Plan sprint" --icon "✅" --content "## Retro\n- went well: ..."

# Clear the icon
personal-tracker update --id 1f3b… --no-icon
```

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

# "Show me what's on today, with ids so I can edit them"
personal-tracker list-today --show-id

# "Did Notion actually accept the recurring change?"
personal-tracker find --name "Gym"

# "Create a task with an emoji and a checklist body"
personal-tracker add --name "Trip prep" --time 2026-06-20T08:00 \
  --icon "🧳" --content "## Packing\n- [ ] passport\n- [ ] charger"

# "Add notes to an existing task and mark it with a checkmark"
personal-tracker update --name "Trip prep" --icon "✅" --content "Booked the hotel."
```
