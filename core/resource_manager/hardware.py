import psutil

from core.contracts.models import (
    GpuSnapshot,
    HardwareStatus,
    SystemSnapshot,
    utc_now,
)
from core.logging.logger import OximoronLogger

logger = OximoronLogger("hardware")

class HardwareService:
    def __init__(self):
        self._nvml_initialized = False
        self._nvml_failed_reason: str | None = None
        self._pynvml = None
        self._init_nvml()

    def _init_nvml(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            self._pynvml = pynvml
            self._nvml_initialized = True
            logger.info("NVML initialized successfully.")
        except Exception as e:
            self._nvml_initialized = False
            self._nvml_failed_reason = f"NVML unavailable: {e}"
            logger.warning(f"NVML initialization failed: {e}")

    def get_snapshot(self) -> SystemSnapshot:
        # 1. CPU
        cpu_pct = psutil.cpu_percent(interval=None)

        # 2. RAM
        ram = psutil.virtual_memory()
        ram_total = ram.total
        ram_used = ram.used
        ram_free = ram.available

        # 3. Disks
        disks: dict[str, dict[str, int]] = {}
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks[part.mountpoint] = {
                        "total_bytes": usage.total,
                        "used_bytes": usage.used,
                        "free_bytes": usage.free,
                    }
                except (PermissionError, OSError):
                    continue

        # 4. GPUs
        gpus: list[GpuSnapshot] = []
        gpu_status = HardwareStatus(
            available=self._nvml_initialized,
            reason=self._nvml_failed_reason,
        )

        if self._nvml_initialized and self._pynvml:
            try:
                device_count = self._pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = self._pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = self._pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode("utf-8", errors="replace")
                    
                    mem = self._pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    util_pct: float | None = None
                    try:
                        rates = self._pynvml.nvmlDeviceGetUtilizationRates(handle)
                        util_pct = float(rates.gpu)
                    except Exception:
                        pass

                    temp_c: float | None = None
                    try:
                        temp_c = float(self._pynvml.nvmlDeviceGetTemperature(handle, self._pynvml.NVML_TEMPERATURE_GPU))
                    except Exception:
                        pass

                    power_w: float | None = None
                    power_limit_w: float | None = None
                    try:
                        p_mw = self._pynvml.nvmlDeviceGetPowerUsage(handle)
                        power_w = float(p_mw) / 1000.0
                        limit_mw = self._pynvml.nvmlDeviceGetEnforcedPowerLimit(handle)
                        power_limit_w = float(limit_mw) / 1000.0
                    except Exception:
                        pass

                    gpus.append(GpuSnapshot(
                        index=i,
                        name=name,
                        total_memory_bytes=mem.total,
                        used_memory_bytes=mem.used,
                        free_memory_bytes=mem.free,
                        utilization_pct=util_pct,
                        temperature_c=temp_c,
                        power_draw_w=power_w,
                        power_limit_w=power_limit_w,
                    ))
            except Exception as e:
                gpu_status = HardwareStatus(available=False, reason=f"NVML polling error: {e}")

        return SystemSnapshot(
            timestamp=utc_now(),
            cpu_utilization_pct=cpu_pct,
            ram_total_bytes=ram_total,
            ram_used_bytes=ram_used,
            ram_free_bytes=ram_free,
            disks=disks,
            gpus=gpus,
            gpu_status=gpu_status,
        )

    def close(self) -> None:
        if self._nvml_initialized and self._pynvml:
            try:
                self._pynvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml_initialized = False
