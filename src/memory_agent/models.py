from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

JSONScalar = None | bool | int | float | str
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


class RelationalMemoryKind(StrEnum):
    DECISION = "decision"
    EPISODE = "episode"
    FACT = "fact"
    INSIDE_JOKE = "inside_joke"
    MOMENT = "moment"
    OBSERVATION = "observation"
    OPEN_LOOP = "open_loop"
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"
    SELF_MODEL = "self_model"
    TENSION = "tension"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    namespace: str
    kind: str
    content: str
    summary: str
    importance: float
    confidence: float
    metadata: dict[str, JSONValue] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_accessed_at: datetime | None = None
    access_count: int = 0


@dataclass(frozen=True)
class MemoryQueryResult:
    memory: MemoryRecord
    score: float
    reasons: tuple[str, ...] = ()
