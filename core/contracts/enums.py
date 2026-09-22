from enum import Enum


class SupportLevel(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    EXPERIMENTAL = "experimental"

class EngineState(str, Enum):
    UNCONFIGURED = "unconfigured"
    CONFIGURED = "configured"
    STOPPED = "stopped"
    STARTING = "starting"
    LOADING = "loading"
    READY = "ready"
    BUSY = "busy"
    STOPPING = "stopping"
    DEGRADED = "degraded"
    FAILED = "failed"
    EXTERNAL_DETECTED = "external_detected"
    ATTACHED_EXTERNAL = "attached_external"

class JobState(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    WAITING_PERMISSION = "waiting_permission"
    WAITING_RESOURCES = "waiting_resources"
    PREPARING = "preparing"
    RUNNING = "running"
    PERSISTING = "persisting"
    SUCCEEDED = "succeeded"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    OUTCOME_UNKNOWN = "outcome_unknown"

class JobKind(str, Enum):
    CHAT = "chat"
    IMAGE_GENERATION = "image_generation"
    MODEL_SCAN = "model_scan"
    ENGINE_START = "engine_start"
    ENGINE_STOP = "engine_stop"
    ENGINE_RESTART = "engine_restart"
    MODEL_LOAD = "model_load"
    MODEL_UNLOAD = "model_unload"

class ModelRole(str, Enum):
    LLM = "llm"
    DIFFUSION_CHECKPOINT = "diffusion_checkpoint"
    LORA = "lora"
    VAE = "vae"
    CONTROLNET = "controlnet"
    EMBEDDING = "embedding"
    VISION_PROJECTOR = "vision_projector"
    UPSCALER = "upscaler"
    UNKNOWN = "unknown"

class ModelFormat(str, Enum):
    GGUF = "gguf"
    SAFETENSORS = "safetensors"
    CKPT = "ckpt"
    ONNX = "onnx"
    PT = "pt"
    PTH = "pth"
    UNKNOWN = "unknown"

class ProcessStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RECONCILED_DEAD = "reconciled_dead"

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class MessageStatus(str, Enum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"
