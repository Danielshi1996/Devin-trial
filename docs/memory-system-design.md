# Persistent Memory System Design

## Goal

Replace a Hermes-style stateless agent with a lightweight agentic frame that has persistent, inspectable memory.

## Non-goals

- No hosted vector database requirement.
- No mandatory LLM provider dependency.
- No opaque background memory mutation.

## Architecture

```text
user turn
  └─ HermesMemoryAdapter.before_turn(query)
       └─ MemoryStore.search(query)
            └─ SQLite durable store
  └─ model/tool execution with injected memory context
  └─ HermesMemoryAdapter.after_turn(user, assistant)
       └─ MemoryStore.remember(...)
```

## Memory model

Each memory is a durable record:

- `namespace`: isolates users, projects, tenants, or agents.
- `kind`: `observation`, `preference`, `episode`, `fact`, or any project-defined value.
- `content`: full memory text.
- `summary`: short retrieval/display text.
- `importance`: 0.0-1.0 ranking signal.
- `confidence`: 0.0-1.0 trust signal.
- `metadata`: JSON for source IDs, tool names, task IDs, or external references.
- timestamps and access counters for recency/frequency ranking.

## Retrieval

The first shipped retrieval strategy is deterministic lexical ranking:

```text
score = token_overlap + phrase_bonus + importance + confidence + recency + access_frequency
```

This keeps the system dependency-light and testable. A vector scorer can be added later behind the same `MemoryStore.search()` contract.

## Persistence

SQLite is the default store because it is durable, local-first, simple to back up, and works in constrained agent environments. The schema is initialized automatically on first use.

## Hermes integration

The adapter exposes lifecycle hooks:

- `before_turn(message) -> str`: retrieve compact memory context for prompt injection.
- `after_turn(user_message, assistant_response) -> list[MemoryRecord]`: persist the episode.
- `remember(content, kind=..., metadata=...)`: explicit memory writes from tools or higher-level policies.

If Hermes is unavailable, `MemoryAugmentedAgent` provides a tiny callable-responder wrapper for end-to-end use.

## Shipment checklist

- Library API for memory CRUD and retrieval.
- CLI for manual operations.
- Hermes adapter seam.
- Unit tests for persistence, ranking, and lifecycle hooks.
- CI running stdlib unit tests and compile checks.
