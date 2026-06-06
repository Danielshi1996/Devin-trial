from __future__ import annotations

import re
from dataclasses import dataclass

from memory_agent.models import RelationalMemoryKind
from memory_agent.person import PersonContext
from memory_agent.store import MemoryStore

SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")
JOKE_RE = re.compile(r"\b(joke|funny|laughed|lol|inside joke|bit)\b", re.IGNORECASE)
DECISION_RE = re.compile(r"\b(decided|decision|we will|let's|we should|ship|choose|chosen)\b", re.IGNORECASE)
FEELING_RE = re.compile(r"\b(feel|felt|afraid|excited|angry|sad|jealous|motivated|bored|friction|hurt|alive)\b", re.IGNORECASE)
OPEN_LOOP_RE = re.compile(r"\b(later|next|todo|open|unresolved|not sure|figure out|question)\b", re.IGNORECASE)
TENSION_RE = re.compile(r"\b(disagree|wrong|tension|conflict|push back|friction|annoyed|resist)\b", re.IGNORECASE)


@dataclass(frozen=True)
class CuratedMemory:
    kind: RelationalMemoryKind
    content: str
    summary: str
    importance: float


class MemoryCurator:
    def curate(
        self,
        transcript: str,
        *,
        limit: int = 8,
    ) -> list[CuratedMemory]:
        candidates = [
            self._candidate_from_sentence(sentence)
            for sentence in _sentences(transcript)
        ]
        memories = [
            candidate
            for candidate in candidates
            if candidate is not None
        ]
        memories.sort(key=lambda memory: memory.importance, reverse=True)
        return memories[:limit]

    def persist(
        self,
        transcript: str,
        *,
        person: PersonContext,
        store: MemoryStore,
        namespace: str = "default",
        limit: int = 8,
    ) -> list[CuratedMemory]:
        memories = self.curate(transcript, limit=limit)
        if not memories:
            return []

        recent_lines = ["## Curated moments", ""]
        for memory in memories:
            store.remember(
                memory.content,
                namespace=namespace,
                kind=memory.kind.value,
                summary=memory.summary,
                importance=memory.importance,
                metadata={"source": "memory_curator"},
            )
            recent_lines.append(f"- [{memory.kind.value}] {memory.summary}")

        person.append_recent("\n".join(recent_lines))
        return memories

    def _candidate_from_sentence(self, sentence: str) -> CuratedMemory | None:
        normalized = " ".join(sentence.split())
        if len(normalized) < 24:
            return None

        kind = self._kind_for_sentence(normalized)
        if kind is None:
            return None

        summary = normalized if len(normalized) <= 160 else normalized[:157].rstrip() + "..."
        importance = _importance(kind, normalized)
        return CuratedMemory(
            kind=kind,
            content=normalized,
            summary=summary,
            importance=importance,
        )

    def _kind_for_sentence(self, sentence: str) -> RelationalMemoryKind | None:
        if TENSION_RE.search(sentence):
            return RelationalMemoryKind.TENSION
        if DECISION_RE.search(sentence):
            return RelationalMemoryKind.DECISION
        if FEELING_RE.search(sentence):
            return RelationalMemoryKind.MOMENT
        if JOKE_RE.search(sentence):
            return RelationalMemoryKind.INSIDE_JOKE
        if OPEN_LOOP_RE.search(sentence):
            return RelationalMemoryKind.OPEN_LOOP
        return None


def _sentences(transcript: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in SENTENCE_RE.split(transcript)
        if sentence.strip()
    ]


def _importance(kind: RelationalMemoryKind, sentence: str) -> float:
    base = {
        RelationalMemoryKind.TENSION: 0.9,
        RelationalMemoryKind.DECISION: 0.82,
        RelationalMemoryKind.MOMENT: 0.78,
        RelationalMemoryKind.INSIDE_JOKE: 0.72,
        RelationalMemoryKind.OPEN_LOOP: 0.7,
    }.get(kind, 0.6)
    emphasis = min(sentence.count("!") * 0.02, 0.08)
    return min(base + emphasis, 1.0)
