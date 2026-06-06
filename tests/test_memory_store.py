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
            self.assertFalse(store.forget("missing-id"))
            store.close()

    def test_search_edge_cases_and_access_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite")
            memory = store.remember("The quick brown fox", namespace="test")

            self.assertEqual(store.search("", namespace="test"), [])
            self.assertEqual(store.search("a", namespace="test"), [])

            result = store.search("quick", namespace="test", record_access=False)[0]
            self.assertEqual(result.memory.access_count, 0)

            store.search("quick", namespace="test", record_access=True)
            accessed = store.get(memory.id)
            self.assertIsNotNone(accessed)
            if accessed is not None:
                self.assertEqual(accessed.access_count, 1)
            store.close()

    def test_search_candidate_limit_is_configurable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite")
            store.remember("old unique needle", namespace="test", kind="fact")
            store.remember("new unrelated haystack", namespace="test", kind="fact")

            limited = store.search("needle", namespace="test", candidate_limit=1)
            unlimited = store.search("needle", namespace="test", candidate_limit=None)

            self.assertFalse(any("needle" in result.memory.content for result in limited))
            self.assertTrue(any("needle" in result.memory.content for result in unlimited))
            store.close()

    def test_metadata_is_immutable_on_loaded_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite")
            memory = store.remember(
                "Metadata should be immutable",
                namespace="test",
                metadata={"source": "unit"},
            )
            loaded = store.get(memory.id)

            self.assertIsNotNone(loaded)
            if loaded is not None:
                with self.assertRaises(TypeError):
                    loaded.metadata["source"] = "mutated"
            store.close()

    def test_prune_removes_low_priority_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite")
            store.remember("high priority", namespace="test", importance=1.0)
            store.remember("low priority one", namespace="test", importance=0.1)
            store.remember("low priority two", namespace="test", importance=0.1)

            removed = store.prune(namespace="test", max_memories=1)
            remaining = store.list_memories(namespace="test", limit=None)

            self.assertEqual(removed, 2)
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0].content, "high priority")
            store.close()

    def test_context_manager_closes_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with MemoryStore(Path(directory) / "memory.sqlite") as store:
                store.remember("Context managers avoid leaks", namespace="test")

            with self.assertRaises(Exception):
                store.list_memories(namespace="test")


if __name__ == "__main__":
    unittest.main()
