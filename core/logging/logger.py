import logging
import re
from collections import deque
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from core.contracts.models import gen_uuid, utc_now

REDACT_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+"), r"\1[REDACTED]"),
    (re.compile(r"(api_key|token|password|secret)[=:]\s*['\"]?[A-Za-z0-9_\-\.]+['\"]?", re.IGNORECASE), r"\1=[REDACTED]"),
]

def redact_text(text: str) -> str:
    for pattern, replacement in REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

class LogEntry(BaseModel):
    id: str = Field(default_factory=gen_uuid)
    timestamp: datetime = Field(default_factory=utc_now)
    level: str
    component: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)

class LogBuffer:
    def __init__(self, max_entries: int = 5000):
        self.max_entries = max_entries
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)

    def append(self, level: str, component: str, message: str, context: dict[str, Any] | None = None) -> LogEntry:
        clean_msg = redact_text(message)
        entry = LogEntry(
            level=level.upper(),
            component=component,
            message=clean_msg,
            context=context or {},
        )
        self._entries.append(entry)
        return entry

    def query(
        self,
        level: str | None = None,
        component: str | None = None,
        limit: int = 100,
        before_id: str | None = None,
    ) -> list[LogEntry]:
        results = list(self._entries)
        if before_id:
            idx = next((i for i, e in enumerate(results) if e.id == before_id), None)
            if idx is not None:
                results = results[:idx]
        if level:
            results = [e for e in results if e.level == level.upper()]
        if component:
            results = [e for e in results if e.component == component]
        return results[-limit:]

# Global memory log buffer
memory_log_buffer = LogBuffer(max_entries=5000)

class OximoronLogger:
    def __init__(self, component: str):
        self.component = component
        self._py_logger = logging.getLogger(f"oximoron.{component}")

    def info(self, msg: str, **kwargs: Any) -> None:
        memory_log_buffer.append("INFO", self.component, msg, kwargs)
        self._py_logger.info(redact_text(msg))

    def warning(self, msg: str, **kwargs: Any) -> None:
        memory_log_buffer.append("WARNING", self.component, msg, kwargs)
        self._py_logger.warning(redact_text(msg))

    def error(self, msg: str, **kwargs: Any) -> None:
        memory_log_buffer.append("ERROR", self.component, msg, kwargs)
        self._py_logger.error(redact_text(msg))

    def debug(self, msg: str, **kwargs: Any) -> None:
        memory_log_buffer.append("DEBUG", self.component, msg, kwargs)
        self._py_logger.debug(redact_text(msg))
