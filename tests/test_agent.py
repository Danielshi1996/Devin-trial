from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory_agent import HermesMemoryAdapter, MemoryAugmentedAgent, MemoryStore


class AgentTests(unittest.TestCase):
    def test_agent_injects_memory_context_before_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite")
            store.remember(
                "Daniel prefers concise updates",
                namespace="agent",
                kind="preference",
                importance=0.9,
            )
            captured_prompts: list[str] = []

            def responder(prompt: str) -> str:
                captured_prompts.append(prompt)
                return "Keep updates concise."

            agent = MemoryAugmentedAgent(store, responder, namespace="agent")
            response = agent.run("What communication style should I use?")

            self.assertEqual(response, "Keep updates concise.")
            self.assertIn("Daniel prefers concise updates", captured_prompts[0])
            self.assertTrue(store.search("Keep updates concise", namespace="agent"))
            store.close()

    def test_hermes_adapter_persists_turns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite")
            adapter = HermesMemoryAdapter(store, namespace="hermes")

            adapter.after_turn(
                "Remember my preferred database is SQLite",
                "I will use SQLite for local persistence.",
            )
            context = adapter.before_turn("Which database should be used?")

            self.assertIn("SQLite", context)
            store.close()


if __name__ == "__main__":
    unittest.main()
