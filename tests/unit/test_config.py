from pathlib import Path

import pytest

from core.config.manager import ConfigManager
from core.contracts.errors import ErrorCode, OximoronException


def test_default_config_generation(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    mgr = ConfigManager(config_path=cfg_file)
    cfg = mgr.load()

    assert cfg.schema_version == 1
    assert cfg.revision == 1
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.preferred_port == 6969
    assert cfg_file.exists()

def test_atomic_save_and_revision_increment(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    mgr = ConfigManager(config_path=cfg_file)
    cfg = mgr.load()
    assert cfg.revision == 1

    # Modify and save
    cfg.server.preferred_port = 7000
    updated = mgr.save(cfg, expected_revision=1)
    assert updated.revision == 2
    assert updated.server.preferred_port == 7000

    # Reload from disk
    reloaded = mgr.load()
    assert reloaded.revision == 2
    assert reloaded.server.preferred_port == 7000

def test_optimistic_revision_conflict(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    mgr = ConfigManager(config_path=cfg_file)
    cfg = mgr.load()

    # Try saving with wrong expected revision
    with pytest.raises(OximoronException) as exc_info:
        mgr.save(cfg, expected_revision=99)
    assert exc_info.value.code == ErrorCode.CONFLICT
