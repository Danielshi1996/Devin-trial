from __future__ import annotations

from memory_agent.models import JSONValue, MemoryRecord
from memory_agent.store import MemoryStore


class HermesMemoryAdapter:
    def __init__(
        self,
        store: MemoryStore,
        *,
        namespace: str = "default",
        context_limit: int = 5,
    ) -> None:
        self.store = store
        self.namespace = namespace
        self.context_limit = context_limit

    def before_turn(self, user_message: str) -> str:
        return self.store.context(
            user_message,
            namespace=self.namespace,
            limit=self.context_limit,
        )

    def after_turn(
        self,
        user_message: str,
        assistant_response: str,
        *,
        metadata: dict[str, JSONValue] | None = None,
    ) -> list[MemoryRecord]:
        shared_metadata = {"source": "hermes_adapter", **(metadata or {})}
        return [
            self.store.remember(
                user_message,
                namespace=self.namespace,
                kind="observation",
                summary=f"User message: {user_message[:120]}",
                importance=0.35,
                metadata=shared_metadata,
                deduplicate=True,
            ),
            self.store.remember(
                assistant_response,
                namespace=self.namespace,
                kind="episode",
                summary=f"Assistant response: {assistant_response[:120]}",
                importance=0.3,
                metadata=shared_metadata,
                deduplicate=True,
            ),
        ]

    def remember(
        self,
        content: str,
        *,
        kind: str = "fact",
        summary: str | None = None,
        importance: float = 0.6,
        confidence: float = 1.0,
        metadata: dict[str, JSONValue] | None = None,
    ) -> MemoryRecord:
        return self.store.remember(
            content,
            namespace=self.namespace,
            kind=kind,
            summary=summary,
            importance=importance,
            confidence=confidence,
            metadata={"source": "explicit_memory", **(metadata or {})},
            deduplicate=True,
        )
