from collections.abc import Callable
from typing import Any

from misra_platform.core.logging import get_logger

logger = get_logger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            handler(payload)
        logger.info("domain_event_published", event_type=event_type, handler_count=len(handlers))


event_bus = EventBus()
