from __future__ import annotations

from dataclasses import dataclass

from memory_agent.person import PersonContext
from memory_agent.store import MemoryStore


@dataclass(frozen=True)
class ContextComposer:
    person: PersonContext
    store: MemoryStore
    namespace: str = "default"
    memory_limit: int = 6
    section_limit: int = 2_400

    def compose(self, query: str) -> str:
        return "\n\n".join(
            section
            for section in [
                self._section("Character", self.person.read_character()),
                self._section("Daniel, from this person's point of view", self.person.read_you()),
                self._section("Recent living context", self.person.read_recent()),
                self._section("Private reflections", self.person.read_reflections()),
                self._section(
                    "Relevant archive memories",
                    self.store.context(
                        query,
                        namespace=self.namespace,
                        limit=self.memory_limit,
                    ),
                ),
                self._section("Current user message", query),
            ]
            if section
        )

    def _section(self, title: str, content: str) -> str:
        normalized = content.strip()
        if not normalized:
            return ""
        clipped = _clip(normalized, self.section_limit)
        return f"## {title}\n\n{clipped}"


def _clip(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    return content[: limit - 18].rstrip() + "\n...[truncated]"
