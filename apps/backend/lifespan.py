import os
from contextlib import asynccontextmanager

import psutil
from fastapi import FastAPI

from core.config.manager import ConfigManager
from core.contracts.models import RuntimeDiscoveryRecord, gen_uuid
from core.events.broadcaster import EventBroadcaster
from core.logging.logger import OximoronLogger
from core.persistence.database import DatabaseManager
from core.resource_manager.hardware import HardwareService
from core.secrets.manager import SecretManager
from core.supervisor.lock import SupervisorLock

logger = OximoronLogger("lifespan")

@asynccontextmanager
async def lifespan(app: FastAPI):
    instance_id = gen_uuid()
    logger.info(f"Starting OXIMORON backend supervisor instance {instance_id}...")

    # 1. Configuration
    config_manager = ConfigManager()
    config = config_manager.load()
    app.state.config_manager = config_manager

    # 2. Supervisor Lock
    supervisor_lock = SupervisorLock()
    supervisor_lock.acquire()
    app.state.supervisor_lock = supervisor_lock

    # 3. Database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    app.state.db_manager = db_manager

    # 4. Secrets & Auth
    secret_manager = SecretManager()
    token = secret_manager.get_or_create_token()
    app.state.secret_manager = secret_manager
    app.state.api_token = token

    # 5. Events & WebSocket Broadcaster
    broadcaster = EventBroadcaster(supervisor_instance_id=instance_id)
    app.state.event_broadcaster = broadcaster

    # 6. Hardware Service
    hw_service = HardwareService()
    app.state.hardware_service = hw_service

    # 7. Write Discovery Record
    current_proc = psutil.Process(os.getpid())
    host = config.server.host
    port = getattr(app.state, "active_port", config.server.preferred_port)
    discovery_record = RuntimeDiscoveryRecord(
        supervisor_instance_id=instance_id,
        pid=os.getpid(),
        create_time=current_proc.create_time(),
        host=host,
        port=port,
        base_url=f"http://{host}:{port}/api/v1",
        credential_file=str(secret_manager.credential_path),
    )
    supervisor_lock.write_discovery(discovery_record)
    app.state.discovery_record = discovery_record

    logger.info(f"OXIMORON supervisor ready at {discovery_record.base_url}")

    try:
        yield
    finally:
        logger.info("Shutting down OXIMORON backend supervisor...")
        hw_service.close()
        await db_manager.close()
        supervisor_lock.release()
        logger.info("OXIMORON shutdown complete.")
