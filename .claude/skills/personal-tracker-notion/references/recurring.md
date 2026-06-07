# `Repeat` / `--recurring` values

The `Repeat` Notion select (a.k.a. `recurring_type` in code, `--recurring` on the CLI) drives how `poll` advances a done task's `Do on` to the next occurrence. The set of accepted values is defined in `src/personal_tracker/notion/recurring.py`.

If `Repeat = once`, the task is not advanced — it just stays done.

## Fixed values

| Value | Next `Do on` is… |
|---|---|
| `once` | (no advance) |
| `daily` | +1 day |
| `bi-daily` | +2 days |
| `bi-daily-on-weekday` | +2 days, then skip forward to the next weekday if it lands on Sat/Sun |
| `weekly` | +1 week |
| `bi-weekly` | +2 weeks |
| `monthly` | +1 month |
| `bi-monthly` | +2 months |
| `annually` / `yearly` | +1 year |
| `weekday` | the next Mon–Fri after current |
| `weekend` | the next Sat or Sun after current |

## `every N days` (N = 1..9)

```text
every 1 days
every 2 days
…
every 9 days
```

**Caveat — this adds `N + 1` days, not `N`.** That's the original Ruby behavior preserved verbatim; do not "fix" it. If the user wants strictly N days, suggest `every (N-1) days` or one of the named values.

## Weekday list

A hyphen-separated list of three-letter weekday abbreviations, lowercase:

```text
mon
tue-thu
mon-wed-fri
sat-sun
```

The next `Do on` is the next listed weekday after current. Mixed orders are tolerated but stick to chronological order (`mon-wed-fri`, not `fri-wed-mon`) for readability.

## Advance loop semantics

`next_time_by_recurring_type` runs the per-rule step **in a loop** until the result is `>= now`. So if a `daily` task was last done two weeks ago, one poll advances it to *today*, not two weeks ago. That's intentional — it gracefully handles late completions and missed polls.

## Quick examples for `--recurring`

```fish
personal-tracker add --name "Standup"  --time 2026-06-08T09:00 --recurring weekday
personal-tracker add --name "Gym"      --time 2026-06-08T18:00 --recurring tue-thu
personal-tracker add --name "Rent"     --time 2026-06-01T09:00 --recurring monthly
personal-tracker add --name "Backup"   --time 2026-06-08T03:00 --recurring "every 3 days"
```

Anything outside this set will be stored verbatim but `poll` will never advance it.
