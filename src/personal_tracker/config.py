from __future__ import annotations

import os
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_TZ = "Asia/Ho_Chi_Minh"
ENV_CONFIG_DIR = "PERSONAL_TRACKER_CONFIG"
APP_DIR_NAME = "personal-tracker"
SETTINGS_FILENAME = "settings.yml"
LOCAL_SETTINGS_FILENAME = "settings.local.yml"


class Settings:
    def __init__(self, data: dict[str, Any], notion_token: str | None, tz: str) -> None:
        self._data = data
        self.notion_token = notion_token
        self.tz = tz

    @property
    def definition_fields(self) -> dict[str, str]:
        return self._data["notion"]["definition_fields"]

    @property
    def databases(self) -> dict[str, str]:
        return self._data["notion"]["databases"]

    @property
    def skip_time(self) -> bool:
        mode = self._data.get("mode") or {}
        return bool(mode.get("skip_time"))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def resolve_config_dir() -> Path:
    """Pick the config directory used when ``config_dir`` isn't passed explicitly.

    Order: ``$PERSONAL_TRACKER_CONFIG`` → ``$CWD/config`` (if it contains
    settings.yml — keeps the in-repo dev workflow) → ``$XDG_CONFIG_HOME/personal-tracker``
    → ``~/.config/personal-tracker``.
    """
    env_dir = os.environ.get(ENV_CONFIG_DIR)
    if env_dir:
        return Path(env_dir).expanduser()

    cwd_config = Path.cwd() / "config"
    if (cwd_config / SETTINGS_FILENAME).exists():
        return cwd_config

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / APP_DIR_NAME

    return Path.home() / ".config" / APP_DIR_NAME


def _read_packaged_defaults() -> dict[str, Any]:
    text = (
        resources.files("personal_tracker._defaults")
        .joinpath(SETTINGS_FILENAME)
        .read_text(encoding="utf-8")
    )
    return yaml.safe_load(text) or {}


def _load_env_files(config_dir: Path) -> None:
    candidates = [config_dir / ".env", Path.cwd() / ".env"]
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not path.exists():
            seen.add(resolved)
            continue
        seen.add(resolved)
        load_dotenv(path, override=False)


def load_settings(config_dir: Path | None = None) -> Settings:
    resolved_dir = config_dir if config_dir is not None else resolve_config_dir()
    _load_env_files(resolved_dir)

    base_path = resolved_dir / SETTINGS_FILENAME
    local_path = resolved_dir / LOCAL_SETTINGS_FILENAME

    if base_path.exists():
        with base_path.open() as f:
            data = yaml.safe_load(f) or {}
    else:
        data = _read_packaged_defaults()

    if local_path.exists():
        with local_path.open() as f:
            local = yaml.safe_load(f) or {}
        data = _deep_merge(data, local)

    return Settings(
        data=data,
        notion_token=os.environ.get("NOTION_SECRET_TOKEN"),
        tz=os.environ.get("TZ", DEFAULT_TZ),
    )
