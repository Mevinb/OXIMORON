import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utc_now() -> datetime:
    return datetime.now(UTC)

def gen_uuid() -> str:
    return str(uuid.uuid4())

class EngineModel(Base):
    __tablename__ = "engines"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    adapter_key = Column(String(64), nullable=False)
    display_name = Column(String(128), nullable=False)
    config_key = Column(String(64), unique=True, nullable=False)
    version = Column(String(64), nullable=True)
    capability_json = Column(JSON, nullable=False, default=dict)
    observed_state = Column(String(32), nullable=False, default="unconfigured")
    endpoint = Column(String(256), nullable=True)
    last_health_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    processes = relationship("ProcessModel", back_populates="engine", cascade="all, delete-orphan")

class ProcessModel(Base):
    __tablename__ = "processes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    engine_id = Column(String(36), ForeignKey("engines.id"), nullable=False, index=True)
    pid = Column(Integer, nullable=False)
    create_time = Column(Float, nullable=False)
    executable_identity = Column(String(512), nullable=False)
    command_fingerprint = Column(String(128), nullable=False)
    group_id = Column(Integer, nullable=False)
    ownership = Column(String(32), default="owned", nullable=False)
    port = Column(Integer, nullable=False)
    model_id = Column(String(36), nullable=True)
    status = Column(String(32), default="starting", nullable=False)
    start_at = Column(DateTime, default=utc_now, nullable=False)
    exit_at = Column(DateTime, nullable=True)
    exit_code = Column(Integer, nullable=True)
    log_ref = Column(String(512), nullable=True)

    engine = relationship("EngineModel", back_populates="processes")

class ModelEntity(Base):
    __tablename__ = "models"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(256), nullable=False, index=True)
    role = Column(String(64), default="unknown", nullable=False)
    format = Column(String(32), default="unknown", nullable=False)
    architecture = Column(String(64), nullable=True)
    quantization = Column(String(32), nullable=True)
    parameter_count = Column(Integer, nullable=True)
    context_length = Column(Integer, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    metadata_provenance = Column(String(64), default="inferred", nullable=False)
    favorite = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    files = relationship("ModelFileModel", back_populates="model", cascade="all, delete-orphan")

class ModelFileModel(Base):
    __tablename__ = "model_files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    model_id = Column(String(36), ForeignKey("models.id"), nullable=False, index=True)
    relative_role = Column(String(64), default="primary", nullable=False)
    byte_size = Column(Integer, nullable=False)
    full_hash = Column(String(128), nullable=True, index=True)
    hash_algorithm = Column(String(32), default="sha256", nullable=False)
    hash_state = Column(String(32), default="pending", nullable=False)
    bundle_index = Column(Integer, default=0, nullable=False)

    model = relationship("ModelEntity", back_populates="files")
    locations = relationship("ModelLocationModel", back_populates="model_file", cascade="all, delete-orphan")

class ModelLocationModel(Base):
    __tablename__ = "model_locations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    model_file_id = Column(String(36), ForeignKey("model_files.id"), nullable=False, index=True)
    root_id = Column(String(36), nullable=True)
    display_path = Column(String(1024), nullable=False)
    canonical_path = Column(String(1024), unique=True, nullable=False)
    device_id = Column(Integer, default=0, nullable=False)
    inode = Column(Integer, default=0, nullable=False)
    mtime_ns = Column(Integer, default=0, nullable=False)
    available = Column(Boolean, default=True, nullable=False)
    managed = Column(Boolean, default=False, nullable=False)

    model_file = relationship("ModelFileModel", back_populates="locations")

class ModelRootModel(Base):
    __tablename__ = "model_roots"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    path = Column(String(1024), unique=True, nullable=False)
    recursive = Column(Boolean, default=True, nullable=False)
    depth_limit = Column(Integer, default=4, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    scan_status = Column(String(32), default="idle", nullable=False)
    last_scan_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    kind = Column(String(64), nullable=False, index=True)
    workspace_id = Column(String(36), default="default", nullable=False, index=True)
    engine_id = Column(String(36), nullable=True, index=True)
    model_id = Column(String(36), nullable=True, index=True)
    state = Column(String(32), default="queued", nullable=False, index=True)
    request_snapshot = Column(JSON, default=dict, nullable=False)
    policy_revision = Column(Integer, default=1, nullable=False)
    parent_job_id = Column(String(36), nullable=True)
    cancel_requested_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    outcome_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    events = relationship("JobEventModel", back_populates="job", cascade="all, delete-orphan")

class JobEventModel(Base):
    __tablename__ = "job_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    event_type = Column(String(64), nullable=False)
    payload_json = Column(JSON, default=dict, nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("job_id", "sequence", name="uq_job_sequence"),
    )

    job = relationship("JobModel", back_populates="events")

class ConversationModel(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    workspace_id = Column(String(36), default="default", nullable=False, index=True)
    title = Column(String(256), default="New Conversation", nullable=False)
    default_model_id = Column(String(36), nullable=True)
    system_prompt = Column(Text, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")

class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    role = Column(String(32), nullable=False)
    content = Column(Text, default="", nullable=False)
    status = Column(String(32), default="completed", nullable=False)
    job_id = Column(String(36), nullable=True)
    model_id = Column(String(36), nullable=True)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    usage_source = Column(String(32), default="estimated", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_conv_sequence"),
    )

    conversation = relationship("ConversationModel", back_populates="messages")

class GenerationModel(Base):
    __tablename__ = "generations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    job_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="default", nullable=False)
    engine_id = Column(String(36), nullable=False)
    model_id = Column(String(36), nullable=True)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, default="", nullable=False)
    requested_settings_json = Column(JSON, default=dict, nullable=False)
    effective_settings_json = Column(JSON, default=dict, nullable=False)
    seed = Column(Integer, nullable=False)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String(32), default="completed", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    artifacts = relationship("ArtifactModel", back_populates="generation", cascade="all, delete-orphan")

class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    generation_id = Column(String(36), ForeignKey("generations.id"), nullable=True, index=True)
    kind = Column(String(32), default="image", nullable=False)
    relative_path = Column(String(512), nullable=False)
    absolute_path = Column(String(1024), nullable=False)
    media_type = Column(String(64), default="image/png", nullable=False)
    byte_size = Column(Integer, nullable=False)
    hash = Column(String(128), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    provenance_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    generation = relationship("GenerationModel", back_populates="artifacts")

class IdempotencyKeyModel(Base):
    __tablename__ = "idempotency_keys"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    scope = Column(String(64), nullable=False)
    operation = Column(String(64), nullable=False)
    key_hash = Column(String(128), nullable=False, index=True)
    payload_hash = Column(String(128), nullable=False)
    job_id = Column(String(36), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("scope", "operation", "key_hash", name="uq_idempotency_scope_op_key"),
    )

class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default="default")
    name = Column(String(128), default="Default", nullable=False)
    preset_json = Column(JSON, default=dict, nullable=False)
    privacy_policy_json = Column(JSON, default=dict, nullable=False)
    allowed_roots_json = Column(JSON, default=list, nullable=False)
    revision = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

class SettingsEntity(Base):
    __tablename__ = "settings"

    key = Column(String(128), primary_key=True)
    value_json = Column(JSON, default=dict, nullable=False)
    schema_version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
