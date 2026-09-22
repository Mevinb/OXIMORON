import json
import struct
from pathlib import Path
from typing import Any

from core.contracts.enums import ModelFormat, ModelRole

GGUF_MAGIC = b"GGUF"

def parse_gguf_metadata(file_path: Path, max_header_bytes: int = 1_000_000) -> dict[str, Any]:
    """
    Safely reads GGUF header without loading tensor data or using unsafe deserialization.
    """
    metadata: dict[str, Any] = {"format": ModelFormat.GGUF.value}
    try:
        with open(file_path, "rb") as f:
            magic = f.read(4)
            if magic != GGUF_MAGIC:
                return {"error": "Invalid GGUF magic bytes", "format": ModelFormat.UNKNOWN.value}

            version = struct.unpack("<I", f.read(4))[0]
            metadata["gguf_version"] = version

            # Read tensor count and kv count
            if version >= 2:
                tensor_count, kv_count = struct.unpack("<QQ", f.read(16))
            else:
                tensor_count, kv_count = struct.unpack("<II", f.read(8))

            metadata["tensor_count"] = tensor_count
            metadata["kv_count"] = min(kv_count, 1000)

            # Guess role based on filename/magic
            name_lower = file_path.name.lower()
            if any(k in name_lower for k in ["llama", "qwen", "mistral", "gemma", "phi", "deepseek"]):
                metadata["role"] = ModelRole.LLM.value
            elif any(k in name_lower for k in ["flux", "sd", "diffusion"]):
                metadata["role"] = ModelRole.DIFFUSION_CHECKPOINT.value
            else:
                metadata["role"] = ModelRole.LLM.value

            return metadata
    except Exception as e:
        return {"error": str(e), "format": ModelFormat.GGUF.value}

def parse_safetensors_metadata(file_path: Path) -> dict[str, Any]:
    """
    Safely reads safetensors JSON header (first 8 bytes little-endian size, then JSON header).
    Never loads tensor data.
    """
    metadata: dict[str, Any] = {"format": ModelFormat.SAFETENSORS.value}
    try:
        with open(file_path, "rb") as f:
            size_bytes = f.read(8)
            if len(size_bytes) < 8:
                return {"error": "File too small for safetensors", "format": ModelFormat.UNKNOWN.value}

            header_size = struct.unpack("<Q", size_bytes)[0]
            if header_size > 50_000_000:  # 50 MB sanity limit on header
                return {"error": "Safetensors header suspiciously large", "format": ModelFormat.SAFETENSORS.value}

            header_json_bytes = f.read(header_size)
            header_dict = json.loads(header_json_bytes.decode("utf-8"))

            metadata["header_keys_count"] = len(header_dict)
            file_meta = header_dict.get("__metadata__", {})
            metadata["user_metadata"] = {k: str(v)[:200] for k, v in file_meta.items()}

            # Determine role from metadata or keys
            name_lower = file_path.name.lower()
            if "lora" in name_lower or "lora" in str(file_meta).lower():
                metadata["role"] = ModelRole.LORA.value
            elif "vae" in name_lower:
                metadata["role"] = ModelRole.VAE.value
            elif "controlnet" in name_lower:
                metadata["role"] = ModelRole.CONTROLNET.value
            elif any(k in name_lower for k in ["xl", "sd", "diffusion", "checkpoint", "flux"]):
                metadata["role"] = ModelRole.DIFFUSION_CHECKPOINT.value
            else:
                metadata["role"] = ModelRole.DIFFUSION_CHECKPOINT.value

            return metadata
    except Exception as e:
        return {"error": str(e), "format": ModelFormat.SAFETENSORS.value}
