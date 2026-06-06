# Persistent Memory System Design

## Goal

Replace a Hermes-style stateless agent with a lightweight agentic frame that has persistent, inspectable memory.

The second design goal is relational: the agent should not only remember facts, but preserve the moments that make it feel like the same person tomorrow.

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

Relational mode adds controlled context files around the archive:

```text
person/
  character.md      who the agent is
  you.md            who the human is from the agent's point of view
  recent.md         living moments that changed something
  reflections.md    private synthesis / alone time
  archive.sqlite    durable searchable memory
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

Relational memory uses additional `kind` values:

- `moment`: emotionally meaningful exchange.
- `tension`: disagreement, friction, or unresolved conflict.
- `open_loop`: a loose thread to return to later.
- `inside_joke`: shared language or humor.
- `decision`: something chosen together.
- `self_model`: what the agent believes about who the human is becoming.
- `relationship`: what the agent believes is true between the two of them.

## Retrieval

The first shipped retrieval strategy is deterministic lexical ranking:

```text
score = token_overlap + phrase_bonus + importance + confidence + recency + access_frequency
```

This keeps the system dependency-light and testable. A vector scorer can be added later behind the same `MemoryStore.search()` contract.

`search()` is a read by default. Access counters are updated only when callers opt in with `record_access=True`; `context()` opts in because context injection implies the memories were actually used.

## Persistence

SQLite is the default store because it is durable, local-first, simple to back up, and works in constrained agent environments. The schema is initialized automatically on first use.

Duplicate writes can be suppressed with `deduplicate=True`, which the Hermes adapter uses for replay-safe lifecycle calls. `MemoryStore.prune(namespace=..., max_memories=...)` removes low-priority overflow when a namespace grows beyond its configured budget.

## Hermes integration

The adapter exposes lifecycle hooks:

- `before_turn(message) -> str`: retrieve compact memory context for prompt injection.
- `after_turn(user_message, assistant_response) -> list[MemoryRecord]`: persist the episode.
- `remember(content, kind=..., metadata=...)`: explicit memory writes from tools or higher-level policies.

If Hermes is unavailable, `MemoryAugmentedAgent` provides a tiny callable-responder wrapper for end-to-end use.

## Relational curation

Raw conversation is not automatically treated as durable memory. `MemoryCurator` asks a narrower question:

```text
What happened here that would make tomorrow's conversation worse if forgotten?
```

The current implementation is deterministic and dependency-free. It scans transcript sentences for high-signal categories:

- decisions
- feelings / moments
- tension / friction
- inside jokes
- open loops

The curator writes selected memories to `archive.sqlite` and appends a compact bullet list to `recent.md`.

## Context composition

`ContextComposer` builds a prompt context from:

1. `character.md`
2. `you.md`
3. `recent.md`
4. `reflections.md`
5. top-K relevant archive memories
6. current user message

This makes retrieval feel relational instead of purely factual.

## Shipment checklist

- Library API for memory CRUD and retrieval.
- CLI for manual operations.
- Hermes adapter seam.
- Person-context files and relational curation.
- Context composition for character + recent + archive memory.
- Replay-safe deduplication and pruning support.
- Unit tests for persistence, ranking, and lifecycle hooks.
- CI running stdlib unit tests and compile checks.
