# Configuration reference

## `settings.yml`

Full schema with defaults:

```yaml
notion:
  definition_fields:           # Notion column name → internal attribute
    deadline:       "Deadline"
    end_time:       "Do on end"
    is_done:        "Done?"
    recurring_type: "Repeat"
    task_name:      "What to do"
    time_mark:      "Do on"
    remind:         "Remind"
  databases:
    tasks: "<notion database id>"

mode:
  skip_time: false             # true → only send YYYY-MM-DD (drop time-of-day)
```

The values on the right of `definition_fields` are the **literal Notion column names** in the user's database. If their database calls the title column "Task" instead of "What to do", change `task_name: "Task"` — code does not need to change.

`databases.tasks` is the only database key the CLI currently uses. Other keys are accepted but ignored.

## Layering

Three layers, deep-merged in this order:

1. `settings.yml` — checked-in baseline (or the bundled defaults if missing).
2. `settings.local.yml` — gitignored, per-machine overrides. Same shape; only specify the keys you want to change.
3. Environment variables — see below.

A `settings.local.yml` example for prod overrides:

```yaml
notion:
  databases:
    tasks: "1f3b9c8d..."
mode:
  skip_time: true
```

## Environment variables

Loaded from `<config_dir>/.env`, then `./.env`, with `override=False` — i.e. an existing shell variable always wins.

| Variable | Purpose | Required |
|---|---|---|
| `NOTION_SECRET_TOKEN` | Notion integration token (`secret_…`). | yes |
| `TZ` | IANA timezone string. Defaults to `Asia/Ho_Chi_Minh`. | no |

The integration must be **shared with the database** in Notion's UI (Share → invite integration) or all calls return 404.

## `skip_time` — what it actually changes

- `false` (default): `Do on`, `Do on end`, `Deadline` are serialized as full ISO datetimes (`2026-06-08T09:00:00+07:00`). Reminders, time-of-day comparisons work.
- `true`: those fields are serialized as `YYYY-MM-DD`. Notion stores them as date-only. On read, they parse to naive midnight; the CLI normalizes when sorting (`list-today`) and when comparing deadlines (deadlines are treated as overdue all day on the due date).

Don't enable `skip_time` if you care about reminders — a 15-minute reminder window needs a time.

## Timezone behavior

`settings.tz` is applied in three places:

- Parsing CLI datetimes: naive ISO inputs (`2026-06-08T09:00`) get this tz attached.
- Writing to Notion: all datetimes are `astimezone(tz)`'d before serialization.
- Display: `find`, `list-today` print local-tz ISO.

To run in a different tz, set `TZ` in `.env` (or your shell) — there's no `tz:` key in `settings.yml`.

## How `definition_fields` actually flows

- `Task.to_data()` (write path) iterates the user's mapping and serializes each known attribute into Notion's `{property_name: {select|date|checkbox|title: …}}` envelope.
- `Task.from_data()` (read path) does the inverse, pulling each attribute out by the configured column name.

Renaming a column in Notion only requires updating `definition_fields` — no code change. Adding a brand-new column requires code work in `models.py`.
