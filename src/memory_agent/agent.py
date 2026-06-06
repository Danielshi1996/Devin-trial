from __future__ import annotations

from collections.abc import Callable

from memory_agent.store import MemoryStore

Responder = Callable[[str], str]


class MemoryAugmentedAgent:
    def __init__(
        self,
        store: MemoryStore,
        responder: Responder | None = None,
        *,
        namespace: str = "default",
        context_limit: int = 5,
    ) -> None:
        self.store = store
        self.responder = responder or _echo_responder
        self.namespace = namespace
        self.context_limit = context_limit

    def run(self, message: str) -> str:
        memory_context = self.store.context(
            message,
            namespace=self.namespace,
            limit=self.context_limit,
        )
        prompt = f"{memory_context}\n\nUser: {message}"
        response = self.responder(prompt)
        self.store.remember(
            f"User asked: {message}\nAssistant answered: {response}",
            namespace=self.namespace,
            kind="episode",
            summary=f"Conversation about: {message[:120]}",
            importance=0.4,
            metadata={"source": "memory_augmented_agent"},
        )
        return response


def _echo_responder(prompt: str) -> str:
    return f"Received with memory context:\n{prompt}"
