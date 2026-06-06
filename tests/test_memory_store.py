from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory_agent import MemoryStore


class MemoryStoreTests(unittest.TestCase):
    def test_memory_persists_across_store_instances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "memory.sqlite"
            first_store = MemoryStore(db_path)
            first_store.remember(
                "The agent should persist memory in SQLite",
                namespace="test",
                kind="fact",
            )
            first_store.close()

            second_store = MemoryStore(db_path)
            results = second_store.search("persistent SQLite memory", namespace="test")

            self.assertEqual(len(results), 1)
            self.assertIn("SQLite", results[0].memory.content)
            second_store.close()

    def test_search_respects_namespace_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite")
            store.remember("Use Postgres", namespace="tenant-a")
            store.remember("Use SQLite", namespace="tenant-b")

            results = store.search("database SQLite Postgres", namespace="tenant-b")

            self.assertEqual(len(results), 1)
            self.assertIn("SQLite", results[0].memory.content)
            store.close()

    def test_forget_deletes_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite")
            memory = store.remember("Temporary memory", namespace="test")

            self.assertTrue(store.forget(memory.id))
            self.assertEqual(store.search("Temporary", namespace="test"), [])
            store.close()


if __name__ == "__main__":
    unittest.main()
