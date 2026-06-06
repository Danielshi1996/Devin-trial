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
            _episode_content(message, response),
            namespace=self.namespace,
            kind="episode",
            summary=f"Conversation about: {message[:120]}",
            importance=0.4,
            metadata={"source": "memory_augmented_agent"},
        )
        return response


def _echo_responder(prompt: str) -> str:
    return f"Received with memory context:\n{prompt}"


def _episode_content(message: str, response: str) -> str:
    if response.startswith("Received with memory context:"):
        safe_response = "Assistant produced a response using retrieved memory context."
    else:
        safe_response = response[:2_000]
    return f"User asked: {message[:2_000]}\nAssistant answered: {safe_response}"
