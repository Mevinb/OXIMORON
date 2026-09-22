import asyncio
import os
from pathlib import Path
from typing import Any

from sqlalchemy import select

from core.contracts.enums import ModelFormat, ModelRole
from core.contracts.models import gen_uuid, utc_now
from core.logging.logger import OximoronLogger
from core.model_registry.parsers import parse_gguf_metadata, parse_safetensors_metadata
from core.persistence.database import DatabaseManager
from core.persistence.models import ModelEntity, ModelFileModel, ModelLocationModel

logger = OximoronLogger("model_scanner")

EXTENSION_FORMAT_MAP = {
    ".gguf": ModelFormat.GGUF,
    ".safetensors": ModelFormat.SAFETENSORS,
    ".ckpt": ModelFormat.CKPT,
    ".onnx": ModelFormat.ONNX,
    ".pt": ModelFormat.PT,
    ".pth": ModelFormat.PTH,
}

class ModelScanner:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def scan_roots(
        self,
        roots: list[Path],
        depth_limit: int = 4,
        cancel_event: asyncio.Event | None = None,
    ) -> int:
        discovered_count = 0

        for root in roots:
            if not root.exists() or not root.is_dir():
                continue

            logger.info(f"Scanning root directory: {root}")
            for dirpath, _, filenames in os.walk(root):
                if cancel_event and cancel_event.is_set():
                    logger.info("Model scan cancelled.")
                    break

                # Check depth
                rel = Path(dirpath).relative_to(root)
                if len(rel.parts) > depth_limit:
                    continue

                for fn in filenames:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in EXTENSION_FORMAT_MAP:
                        file_path = Path(dirpath) / fn
                        try:
                            await self._register_scanned_file(file_path, ext)
                            discovered_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to index model file {file_path}: {e}")

        return discovered_count

    async def _register_scanned_file(self, file_path: Path, ext: str) -> None:
        canonical_str = str(file_path.resolve())
        stat = file_path.stat()
        byte_size = stat.st_size
        mtime_ns = stat.st_mtime_ns

        # 1. Check if location already registered
        async with self.db.session() as session:
            stmt = select(ModelLocationModel).where(ModelLocationModel.canonical_path == canonical_str)
            res = await session.execute(stmt)
            existing_loc = res.scalar_one_or_none()
            if existing_loc:
                if existing_loc.mtime_ns != mtime_ns:
                    existing_loc.mtime_ns = mtime_ns
                return

        # 2. Parse metadata
        fmt = EXTENSION_FORMAT_MAP.get(ext, ModelFormat.UNKNOWN)
        meta: dict[str, Any] = {}
        role = ModelRole.UNKNOWN

        if fmt == ModelFormat.GGUF:
            meta = parse_gguf_metadata(file_path)
            role = ModelRole(meta.get("role", ModelRole.LLM.value))
        elif fmt == ModelFormat.SAFETENSORS:
            meta = parse_safetensors_metadata(file_path)
            role = ModelRole(meta.get("role", ModelRole.DIFFUSION_CHECKPOINT.value))

        # 3. Create ModelEntity, ModelFile, and ModelLocation
        model_id = gen_uuid()
        file_id = gen_uuid()
        loc_id = gen_uuid()

        async with self.db.session() as session:
            entity = ModelEntity(
                id=model_id,
                name=file_path.stem,
                role=role.value,
                format=fmt.value,
                metadata_json=meta,
                created_at=utc_now(),
            )
            session.add(entity)

            model_file = ModelFileModel(
                id=file_id,
                model_id=model_id,
                relative_role="primary",
                byte_size=byte_size,
                hash_state="pending",
                bundle_index=0,
            )
            session.add(model_file)

            loc = ModelLocationModel(
                id=loc_id,
                model_file_id=file_id,
                display_path=str(file_path),
                canonical_path=canonical_str,
                device_id=stat.st_dev,
                inode=stat.st_ino,
                mtime_ns=mtime_ns,
                available=True,
                managed=False,
            )
            session.add(loc)

        logger.info(f"Registered model: {file_path.stem} ({fmt.value}, {byte_size / 1e6:.1f} MB)")
