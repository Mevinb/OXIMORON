from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    preferred_port: int = 6969
    port_fallback_count: int = 10
    remote_access: bool = False

class PrivacyConfig(BaseModel):
    telemetry: bool = False
    cloud_enabled: bool = False
    nonlocal_network_allowed: bool = False

class StorageConfig(BaseModel):
    model_directory: str = "~/OXIMORON/models"
    generation_directory: str = "~/OXIMORON/generations"
    scan_roots: list[str] = Field(default_factory=list)

class EngineInstanceConfig(BaseModel):
    enabled: bool = False
    executable: str | None = None
    directory: str | None = None
    python_executable: str | None = None
    preferred_port: int = 8080
    startup_timeout_seconds: int = 180

class ResourcesConfig(BaseModel):
    automatic_management: bool = False
    idle_unload_minutes: int = 10
    max_gpu_jobs: int = 1
    vram_reserve_mib: int = 768
    ram_reserve_mib: int = 2048

class DesktopConfig(BaseModel):
    start_with_system: bool = False
    start_minimized: bool = False
    restore_ui_session: bool = True
    start_local_llm: bool = False
    close_action: str = "ask"

class LogsConfig(BaseModel):
    level: str = "info"
    include_prompt_content: bool = False
    max_file_mib: int = 10
    backups_per_source: int = 5
    global_cap_mib: int = 250

class AppConfig(BaseModel):
    schema_version: int = 1
    revision: int = 1
    server: ServerConfig = Field(default_factory=ServerConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    engines: dict[str, EngineInstanceConfig] = Field(
        default_factory=lambda: {
            "llamacpp": EngineInstanceConfig(
                enabled=False,
                executable="/home/mevlec/llama.cpp/build/bin/llama-server",
                preferred_port=8080,
                startup_timeout_seconds=180,
            ),
            "forge": EngineInstanceConfig(
                enabled=False,
                directory="/home/mevlec/Data/forge/stable-diffusion-webui-forge",
                python_executable="/home/mevlec/Data/forge/stable-diffusion-webui-forge/venv/bin/python",
                preferred_port=7860,
                startup_timeout_seconds=300,
            ),
            "fooocus": EngineInstanceConfig(
                enabled=False,
                directory="/home/mevlec/Data/foocus",
                python_executable="/home/mevlec/Data/foocus/fooocus_env/bin/python",
                preferred_port=7865,
                startup_timeout_seconds=300,
            ),
        }
    )
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    desktop: DesktopConfig = Field(default_factory=DesktopConfig)
    logs: LogsConfig = Field(default_factory=LogsConfig)
