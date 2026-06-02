from pathlib import Path

from personal_tracker.config import _deep_merge, load_settings


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
