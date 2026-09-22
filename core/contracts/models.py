import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from core.contracts.enums import (
    EngineState,
    JobKind,
    JobState,
    MessageRole,
    MessageStatus,
    ModelFormat,
    ModelRole,
    ProcessStatus,
)


def utc_now() -> datetime:
    return datetime.now(UTC)

def gen_uuid() -> str:
    return str(uuid.uuid4())

class HardwareStatus(BaseModel):
    available: bool = True
    reason: str | None = None

class GpuSnapshot(BaseModel):
    index: int
    name: str
    total_memory_bytes: int
    used_memory_bytes: int
    free_memory_bytes: int
    utilization_pct: float | None = None
    temperature_c: float | None = None
    power_draw_w: float | None = None
    power_limit_w: float | None = None

class SystemSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    cpu_utilization_pct: float
    ram_total_bytes: int
    ram_used_bytes: int
    ram_free_bytes: int
    disks: dict[str, dict[str, int]]
    gpus: list[GpuSnapshot] = Field(default_factory=list)
    gpu_status: HardwareStatus = Field(default_factory=HardwareStatus)

class EngineCapabilities(BaseModel):
    tasks: list[str] = Field(default_factory=list)
    supported_formats: list[ModelFormat] = Field(default_factory=list)
    streaming: bool = False
    vision: bool = False
    embeddings: bool = False
    tool_calling: bool = False
    concurrency_limit: int = 1
    can_unload: bool = False
    supports_cancellation: bool = False
    notes: str = ""

class EngineDescriptor(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    adapter_key: str
    display_name: str
    config_key: str
    version: str | None = None
    capabilities: EngineCapabilities
    observed_state: EngineState = EngineState.UNCONFIGURED
    endpoint: str | None = None
    pid: int | None = None
    loaded_model_id: str | None = None
    last_health_at: datetime | None = None

class LaunchSpec(BaseModel):
    executable: str
    arguments: list[str] = Field(default_factory=list)
    working_directory: str
    environment: dict[str, str] = Field(default_factory=dict)
    port: int
    host: str = "127.0.0.1"
    ready_probe_path: str = "/health"
    startup_timeout_seconds: int = 60
    graceful_stop_seconds: int = 15

class ProcessRecord(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    engine_id: str
    pid: int
    create_time: float
    command_fingerprint: str
    group_id: int
    port: int
    model_id: str | None = None
    status: ProcessStatus = ProcessStatus.STARTING
    started_at: datetime = Field(default_factory=utc_now)
    exited_at: datetime | None = None
    exit_code: int | None = None
    log_path: str | None = None

class ModelLocation(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    root_path: str
    display_path: str
    canonical_path: str
    byte_size: int
    mtime_ns: int
    available: bool = True
    managed: bool = False

class ModelDescriptor(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    name: str
    role: ModelRole = ModelRole.UNKNOWN
    format: ModelFormat = ModelFormat.UNKNOWN
    architecture: str | None = None
    quantization: str | None = None
    parameter_count: int | None = None
    context_length: int | None = None
    favorite: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    locations: list[ModelLocation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    last_used_at: datetime | None = None

class JobEvent(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    job_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)

class JobDescriptor(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    kind: JobKind
    state: JobState = JobState.QUEUED
    workspace_id: str = "default"
    engine_id: str | None = None
    model_id: str | None = None
    request_snapshot: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    outcome: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

class EventEnvelope(BaseModel):
    schema_version: int = 1
    event_id: str = Field(default_factory=gen_uuid)
    supervisor_instance_id: str
    sequence: int
    job_id: str | None = None
    entity_id: str | None = None
    type: str
    timestamp: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)

class MessageDescriptor(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    conversation_id: str
    sequence: int
    role: MessageRole
    content: str
    status: MessageStatus = MessageStatus.COMPLETED
    model_id: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    created_at: datetime = Field(default_factory=utc_now)

class ConversationDescriptor(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    workspace_id: str = "default"
    title: str = "New Conversation"
    default_model_id: str | None = None
    system_prompt: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    messages: list[MessageDescriptor] = Field(default_factory=list)

class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    model_id: str | None = None
    engine_id: str | None = None
    system_prompt: str | None = None
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int | None = None
    stream: bool = True

class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    engine_id: str | None = None
    model_id: str | None = None
    width: int = 512
    height: int = 512
    steps: int = 20
    cfg_scale: float = 7.0
    sampler_name: str = "Euler a"
    seed: int = -1
    batch_count: int = 1

class ArtifactDescriptor(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    generation_id: str | None = None
    kind: str = "image"
    relative_path: str
    absolute_path: str
    media_type: str = "image/png"
    byte_size: int
    hash: str | None = None
    width: int | None = None
    height: int | None = None
    created_at: datetime = Field(default_factory=utc_now)

class GenerationDescriptor(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    job_id: str
    workspace_id: str = "default"
    engine_id: str
    model_id: str | None = None
    prompt: str
    negative_prompt: str = ""
    requested_settings: dict[str, Any] = Field(default_factory=dict)
    effective_settings: dict[str, Any] = Field(default_factory=dict)
    seed: int
    duration_ms: int | None = None
    status: str = "completed"
    artifacts: list[ArtifactDescriptor] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

class RuntimeDiscoveryRecord(BaseModel):
    supervisor_instance_id: str
    pid: int
    create_time: float
    host: str
    port: int
    base_url: str
    protocol_version: str = "1.0.0"
    credential_file: str
    started_at: datetime = Field(default_factory=utc_now)
