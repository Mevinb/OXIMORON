import json
import struct
from pathlib import Path

import pytest

from core.contracts.enums import ModelFormat, ModelRole
from core.model_registry.scanner import ModelScanner
from core.model_registry.service import ModelService
from core.persistence.database import DatabaseManager


def create_synthetic_gguf(path: Path):
    with open(path, "wb") as f:
        # GGUF Magic + version 3
        f.write(b"GGUF")
        f.write(struct.pack("<I", 3))
        # tensor_count = 10, kv_count = 5
        f.write(struct.pack("<QQ", 10, 5))

def create_synthetic_safetensors(path: Path):
    header = {
        "__metadata__": {"format": "pt", "model_type": "sdxl"},
        "model.diffusion_model.input_blocks.0.0.weight": {"dtype": "F16", "shape": [320, 4, 3, 3], "data_offsets": [0, 92160]},
    }
    header_json = json.dumps(header).encode("utf-8")
    header_len = len(header_json)

    with open(path, "wb") as f:
        f.write(struct.pack("<Q", header_len))
        f.write(header_json)
        f.write(b"\x00" * 100)  # dummy tensor bytes

@pytest.mark.asyncio
async def test_model_scanner_synthetic_files(tmp_path: Path):
    db_file = tmp_path / "test_models.db"
    db = DatabaseManager(db_path=db_file)
    await db.initialize()

    # Create synthetic models folder
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    gguf_file = models_dir / "qwen2-7b-chat.gguf"
    create_synthetic_gguf(gguf_file)

    st_file = models_dir / "sdxl_lightning.safetensors"
    create_synthetic_safetensors(st_file)

    scanner = ModelScanner(db)
    count = await scanner.scan_roots([models_dir])
    assert count == 2

    # Query via ModelService
    svc = ModelService(db)
    all_models = await svc.list_models()
    assert len(all_models) == 2

    # Verify GGUF model
    gguf_models = [m for m in all_models if m.format == ModelFormat.GGUF]
    assert len(gguf_models) == 1
    assert gguf_models[0].name == "qwen2-7b-chat"
    assert gguf_models[0].role == ModelRole.LLM
    assert len(gguf_models[0].locations) == 1

    # Verify Safetensors model
    st_models = [m for m in all_models if m.format == ModelFormat.SAFETENSORS]
    assert len(st_models) == 1
    assert st_models[0].name == "sdxl_lightning"
    assert st_models[0].role == ModelRole.DIFFUSION_CHECKPOINT

    # Toggle favorite
    updated = await svc.toggle_favorite(st_models[0].id)
    assert updated.favorite is True

    await db.close()
