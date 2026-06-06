from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from memory_agent.models import JSONValue, MemoryQueryResult, MemoryRecord

TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")


class MemoryStore:
    def __init__(self, path: str | Path = ".memory.sqlite") -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def remember(
        self,
        content: str,
        *,
        namespace: str = "default",
        kind: str = "observation",
        summary: str | None = None,
        importance: float = 0.5,
        confidence: float = 1.0,
        metadata: dict[str, JSONValue] | None = None,
    ) -> MemoryRecord:
        normalized_content = content.strip()
        if not normalized_content:
            raise ValueError("memory content must not be empty")

        memory_id = str(uuid.uuid4())
        now = _serialize_datetime(_utc_now())
        normalized_summary = (summary or _default_summary(normalized_content)).strip()
        bounded_importance = _clamp(importance)
        bounded_confidence = _clamp(confidence)
        metadata_json = json.dumps(metadata or {}, sort_keys=True)

        self._connection.execute(
            """
            INSERT INTO memories (
                id, namespace, kind, content, summary, importance, confidence,
                metadata_json, created_at, updated_at, last_accessed_at, access_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0)
            """,
            (
                memory_id,
                namespace,
                kind,
                normalized_content,
                normalized_summary,
                bounded_importance,
                bounded_confidence,
                metadata_json,
                now,
                now,
            ),
        )
        self._connection.commit()
        record = self.get(memory_id)
        if record is None:
            raise RuntimeError("memory insert succeeded but record could not be loaded")
        return record

    def get(self, memory_id: str) -> MemoryRecord | None:
        row = self._connection.execute(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        if row is None:
            return None
        return _record_from_row(row)

    def list_memories(
        self,
        *,
        namespace: str = "default",
        kind: str | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        if kind is None:
            rows = self._connection.execute(
                """
                SELECT * FROM memories
                WHERE namespace = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (namespace, limit),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM memories
                WHERE namespace = ? AND kind = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (namespace, kind, limit),
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def search(
        self,
        query: str,
        *,
        namespace: str = "default",
        kind: str | None = None,
        limit: int = 5,
    ) -> list[MemoryQueryResult]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        candidates = self.list_memories(namespace=namespace, kind=kind, limit=1000)
        ranked = [
            _score_memory(memory, query, query_tokens)
            for memory in candidates
        ]
        results = [
            result
            for result in sorted(ranked, key=lambda item: item.score, reverse=True)
            if result.score > 0
        ][:limit]
        self._record_access(result.memory.id for result in results)
        return results

    def context(
        self,
        query: str,
        *,
        namespace: str = "default",
        limit: int = 5,
    ) -> str:
        results = self.search(query, namespace=namespace, limit=limit)
        if not results:
            return "Memory context: no relevant memories found."
        bullets = [
            f"- [{result.memory.kind}] {result.memory.summary}"
            for result in results
        ]
        return "Memory context:\n" + "\n".join(bullets)

    def forget(self, memory_id: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM memories WHERE id = ?",
            (memory_id,),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        self._connection.close()

    def _initialize_schema(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT NOT NULL,
                importance REAL NOT NULL,
                confidence REAL NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_accessed_at TEXT,
                access_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memories_namespace_kind
            ON memories(namespace, kind)
            """
        )
        self._connection.commit()

    def _record_access(self, memory_ids: Iterable[str]) -> None:
        ids = list(memory_ids)
        if not ids:
            return
        now = _serialize_datetime(_utc_now())
        self._connection.executemany(
            """
            UPDATE memories
            SET last_accessed_at = ?, access_count = access_count + 1
            WHERE id = ?
            """,
            [(now, memory_id) for memory_id in ids],
        )
        self._connection.commit()


def _score_memory(
    memory: MemoryRecord,
    query: str,
    query_tokens: set[str],
) -> MemoryQueryResult:
    haystack = f"{memory.summary} {memory.content}"
    memory_tokens = _tokens(haystack)
    overlap = query_tokens & memory_tokens
    reasons: list[str] = []
    score = 0.0

    if overlap:
        score += len(overlap) / math.sqrt(max(len(query_tokens), 1))
        reasons.append("token_overlap")

    if query.strip().lower() in haystack.lower():
        score += 1.5
        reasons.append("phrase_match")

    if memory.importance:
        score += memory.importance * 0.35
        reasons.append("importance")

    if memory.confidence:
        score += memory.confidence * 0.2
        reasons.append("confidence")

    age_seconds = max((_utc_now() - memory.created_at).total_seconds(), 0)
    recency = 1 / (1 + age_seconds / 86_400)
    score += recency * 0.1
    reasons.append("recency")

    if memory.access_count:
        score += min(memory.access_count, 10) * 0.02
        reasons.append("access_frequency")

    return MemoryQueryResult(memory=memory, score=score, reasons=tuple(reasons))


def _record_from_row(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        id=row["id"],
        namespace=row["namespace"],
        kind=row["kind"],
        content=row["content"],
        summary=row["summary"],
        importance=row["importance"],
        confidence=row["confidence"],
        metadata=_json_object_from_text(row["metadata_json"]),
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
        last_accessed_at=_parse_datetime(row["last_accessed_at"])
        if row["last_accessed_at"]
        else None,
        access_count=row["access_count"],
    )


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1
    }


def _default_summary(content: str) -> str:
    return content if len(content) <= 160 else content[:157].rstrip() + "..."


def _clamp(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _json_object_from_text(value: str) -> dict[str, JSONValue]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        return {}
    return {
        str(key): _json_value(item)
        for key, item in parsed.items()
    }


def _json_value(value: object) -> JSONValue:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in value.items()
        }
    return str(value)
