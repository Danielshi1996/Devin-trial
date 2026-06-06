# Persistent Memory Agent

Lightweight persistent memory layer for replacing or augmenting a Hermes-style agent.

The package provides:

- SQLite-backed durable memory storage.
- Deterministic lexical retrieval with recency, importance, and access-frequency ranking.
- A small agent wrapper that injects relevant memories into each turn.
- A Hermes adapter seam that can be called from existing agent lifecycle hooks.
- A relational person context (`character.md`, `you.md`, `recent.md`, `reflections.md`).
- A curator that extracts decisions, tensions, open loops, inside jokes, and moments.
- A CLI for local smoke tests and manual memory inspection.

## Quick start

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests
python3 -m memory_agent.cli --db .memory.sqlite remember "Daniel prefers concise updates"
python3 -m memory_agent.cli --db .memory.sqlite search "communication preference"
python3 -m memory_agent.cli --db .memory.sqlite ask "How should I communicate with Daniel?"
```

## Relational memory quick start

```bash
python3 -m memory_agent.cli init-person ./LinZhi
cat > /tmp/transcript.md <<'EOF'
Daniel: I think the agent should have friction with me, not just agree.
Lin Zhi: Then the first product problem is why you would tell it the truth.
Daniel: Let's make that the center of the next iteration.
EOF
python3 -m memory_agent.cli reflect ./LinZhi /tmp/transcript.md
python3 -m memory_agent.cli context ./LinZhi "I have a scattered idea"
```

This creates a local person folder:

```text
LinZhi/
├── character.md
├── you.md
├── recent.md
├── reflections.md
└── archive.sqlite
```

`recent.md` is the living relationship journal. `archive.sqlite` is the searchable long-term memory.

## Integration shape

Use `HermesMemoryAdapter.before_turn()` to retrieve a compact memory context before model invocation, then call `HermesMemoryAdapter.after_turn()` to persist the user/assistant interaction.

```python
from memory_agent import HermesMemoryAdapter, MemoryStore

store = MemoryStore(".memory/hermes.sqlite")
memory = HermesMemoryAdapter(store, namespace="prod-agent")

memory_context = memory.before_turn(user_message)
prompt = f"{memory_context}\n\nUser: {user_message}"
assistant_response = llm(prompt)
memory.after_turn(user_message, assistant_response)
```

See `docs/memory-system-design.md` for the design and shipment plan.
