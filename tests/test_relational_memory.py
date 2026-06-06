from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from memory_agent import ContextComposer, MemoryCurator, MemoryStore, PersonContext, RelationalMemoryKind


class RelationalMemoryTests(unittest.TestCase):
    def test_person_context_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            person = PersonContext.create(Path(directory) / "LinZhi")

            self.assertTrue(person.character_path.exists())
            self.assertTrue(person.you_path.exists())
            self.assertTrue(person.recent_path.exists())
            self.assertTrue(person.reflections_path.exists())

    def test_curator_extracts_relational_moments_and_updates_recent(self) -> None:
        transcript = """
        Daniel: I think the agent should have friction with me, not just agree.
        Lin Zhi: Then the first product problem is why you would tell it the truth.
        Daniel: Let's make that the center of the next iteration.
        """
        with tempfile.TemporaryDirectory() as directory:
            person = PersonContext.create(Path(directory) / "LinZhi")
            store = MemoryStore(person.archive_path)

            memories = MemoryCurator().persist(
                transcript,
                person=person,
                store=store,
                namespace="linzhi",
            )

            self.assertGreaterEqual(len(memories), 2)
            kinds = {memory.kind for memory in memories}
            self.assertIn(RelationalMemoryKind.TENSION, kinds)
            self.assertIn(RelationalMemoryKind.DECISION, kinds)
            recent = person.read_recent()
            self.assertIn("Curated moments", recent)
            self.assertIn("friction", recent)
            self.assertTrue(store.search("friction agree", namespace="linzhi"))
            store.close()

    def test_context_composer_includes_person_files_and_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            person = PersonContext.create(Path(directory) / "LinZhi")
            person.character_path.write_text(
                "Lin Zhi is warm but refuses lazy conclusions.\n",
                encoding="utf-8",
            )
            person.you_path.write_text(
                "Daniel wants productive friction for scattered ideas.\n",
                encoding="utf-8",
            )
            person.append_recent("- [tension] Daniel asked for friction, not agreement.")
            store = MemoryStore(person.archive_path)
            store.remember(
                "Daniel is motivated by agents that push back with care.",
                namespace="linzhi",
                kind=RelationalMemoryKind.RELATIONSHIP.value,
                importance=0.9,
            )

            context = ContextComposer(person, store, namespace="linzhi").compose(
                "I have a scattered idea"
            )

            self.assertIn("## Character", context)
            self.assertIn("refuses lazy conclusions", context)
            self.assertIn("## Daniel, from this person's point of view", context)
            self.assertIn("productive friction", context)
            self.assertIn("## Recent living context", context)
            self.assertIn("## Relevant archive memories", context)
            self.assertIn("push back with care", context)
            store.close()

    def test_cli_relational_flow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "LinZhi"
            transcript = Path(directory) / "transcript.md"
            transcript.write_text(
                "Daniel: I feel bored when the agent agrees too easily.\n"
                "Lin Zhi: Let's make friction part of the design.\n"
                "Daniel: We will ship the memory system today.\n",
                encoding="utf-8",
            )

            init_result = _run_cli("init-person", str(root))
            reflect_result = _run_cli("reflect", str(root), str(transcript))
            context_result = _run_cli("context", str(root), "How should the agent respond?")

            self.assertEqual(init_result.returncode, 0)
            self.assertEqual(reflect_result.returncode, 0)
            self.assertIn("moment", reflect_result.stdout)
            self.assertIn("decision", reflect_result.stdout)
            self.assertEqual(context_result.returncode, 0)
            self.assertIn("## Recent living context", context_result.stdout)
            self.assertIn("friction", context_result.stdout)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "memory_agent.cli", *args],
        check=False,
        text=True,
        capture_output=True,
    )


if __name__ == "__main__":
    unittest.main()
