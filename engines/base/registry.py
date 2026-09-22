from core.contracts.errors import ErrorCode, OximoronException
from engines.base.adapter import BaseEngineAdapter


class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, BaseEngineAdapter] = {}

    def register(self, adapter: BaseEngineAdapter) -> None:
        self._adapters[adapter.adapter_key] = adapter

    def get(self, adapter_key: str) -> BaseEngineAdapter:
        adapter = self._adapters.get(adapter_key)
        if not adapter:
            raise OximoronException(
                code=ErrorCode.ENGINE_UNSUPPORTED,
                message=f"No engine adapter registered for key '{adapter_key}'",
                status_code=404,
                details={"adapter_key": adapter_key, "available": list(self._adapters.keys())},
            )
        return adapter

    def has(self, adapter_key: str) -> bool:
        return adapter_key in self._adapters

    def list_keys(self) -> list[str]:
        return list(self._adapters.keys())

    def list_adapters(self) -> list[BaseEngineAdapter]:
        return list(self._adapters.values())
