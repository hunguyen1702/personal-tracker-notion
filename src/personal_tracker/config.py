from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_TZ = "Asia/Ho_Chi_Minh"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


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


def load_settings(config_dir: Path | None = None) -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    config_dir = config_dir or CONFIG_DIR
    base_path = config_dir / "settings.yml"
    local_path = config_dir / "settings.local.yml"

    if not base_path.exists():
        raise FileNotFoundError(f"Missing config file: {base_path}")

    with base_path.open() as f:
        data = yaml.safe_load(f) or {}

    if local_path.exists():
        with local_path.open() as f:
            local = yaml.safe_load(f) or {}
        data = _deep_merge(data, local)

    return Settings(
        data=data,
        notion_token=os.environ.get("NOTION_SECRET_TOKEN"),
        tz=os.environ.get("TZ", DEFAULT_TZ),
    )
