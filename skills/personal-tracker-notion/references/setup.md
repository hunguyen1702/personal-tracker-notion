# Setup & install

## Install standalone (no repo checkout)

Pick one — they all install the `personal-tracker` script onto `$PATH`:

```fish
uv tool install git+https://github.com/<fork>/personal-tracker-notion
pipx install     git+https://github.com/<fork>/personal-tracker-notion
pip install --user git+https://github.com/<fork>/personal-tracker-notion
```

`uv tool install` is the default suggestion — it matches the rest of the project's tooling.

## Dev install (from the cloned repo)

```fish
uv sync                                            # creates .venv, installs deps
cp .env.sample .env                                # then fill NOTION_SECRET_TOKEN
cp config/settings.yml config/settings.local.yml   # then set databases.tasks
```

`config/settings.local.yml` is gitignored and deep-merges over `config/settings.yml`. Put per-machine values (production DB id, `skip_time`) there.

All commands in dev are `uv run personal-tracker …`.

## First-run scaffold

```fish
personal-tracker init
```

Writes `settings.yml` (from the bundled defaults) and a `.env` template into the resolved config dir. Prints the next-step checklist.

- Re-run with `--force` to overwrite existing files.
- Override the destination with `--config-dir <path>`.
- A hint is printed about `settings.local.yml` — create it if you want a per-machine override layer.

## Config resolution order

`personal-tracker` looks for its config in this order and uses the first match:

1. `$PERSONAL_TRACKER_CONFIG` — explicit override.
2. `./config/settings.yml` under the cwd — keeps the in-repo dev workflow working.
3. `$XDG_CONFIG_HOME/personal-tracker/`.
4. `~/.config/personal-tracker/`.

If none of those contain a `settings.yml`, the bundled `src/personal_tracker/_defaults/settings.yml` is used silently — no error. That means a missing/typo'd config will *look* like it loaded; if behavior seems off, check which file is actually being read.

`.env` is loaded from `<config_dir>/.env` then `./.env`, with `override=False` — **the shell environment always wins**. To force a new value, `unset` the shell var first or edit it inline.

## Required environment

| Variable | Purpose | Default |
|---|---|---|
| `NOTION_SECRET_TOKEN` | Notion integration token. Required. | — |
| `TZ` | IANA timezone applied to naive datetimes. | `Asia/Ho_Chi_Minh` |

Without `NOTION_SECRET_TOKEN` or `notion.databases.tasks`, every command except `init` exits 1 with a log line naming the missing piece.

## Verifying the install

```fish
personal-tracker --help              # group help, lists subcommands
personal-tracker poll --dry-run      # no writes; confirms creds + DB id work
```

If the dry-run prints a count line ending `dry_run=True`, you're wired up. If it errors on auth, the token is wrong or the integration hasn't been shared with the database in Notion.
