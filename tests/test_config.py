from pathlib import Path

from personal_tracker.config import (
    ENV_CONFIG_DIR,
    _deep_merge,
    load_settings,
    resolve_config_dir,
)


def test_deep_merge_overrides_leaf():
    base = {"a": 1, "b": {"x": 1, "y": 2}}
    over = {"b": {"y": 99, "z": 3}}
    assert _deep_merge(base, over) == {"a": 1, "b": {"x": 1, "y": 99, "z": 3}}


def test_load_settings_merges_local(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "settings.yml").write_text(
        """
notion:
  definition_fields:
    task_name: "What to do"
  databases:
    tasks: ""
mode:
  skip_time: false
"""
    )
    (cfg / "settings.local.yml").write_text(
        """
notion:
  databases:
    tasks: "abcd1234"
mode:
  skip_time: true
"""
    )
    monkeypatch.setenv("NOTION_SECRET_TOKEN", "secret")
    settings = load_settings(config_dir=cfg)
    assert settings.databases["tasks"] == "abcd1234"
    assert settings.skip_time is True
    assert settings.notion_token == "secret"
    assert settings.definition_fields["task_name"] == "What to do"


def test_resolve_config_dir_env_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(ENV_CONFIG_DIR, str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert resolve_config_dir() == tmp_path


def test_resolve_config_dir_falls_back_to_home(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(ENV_CONFIG_DIR, raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert resolve_config_dir() == tmp_path / ".config" / "personal-tracker"


def test_load_settings_uses_packaged_defaults_when_empty(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("NOTION_SECRET_TOKEN", raising=False)
    settings = load_settings(config_dir=tmp_path)
    assert settings.definition_fields["task_name"] == "What to do"
    assert settings.databases["tasks"] == ""
