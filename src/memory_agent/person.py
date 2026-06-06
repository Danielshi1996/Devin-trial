from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


CHARACTER_TEMPLATE = """# Character

Write this like a real person, not a job description.

Include:
- how they speak
- what they care about
- at least one contradiction
- how they handle conflict
"""

YOU_TEMPLATE = """# You

What this person knows about the human from their point of view.
"""

RECENT_TEMPLATE = """# Recent

Moments that changed something belong here.
Not transcripts. Not generic summaries.
"""

REFLECTIONS_TEMPLATE = """# Reflections

The person's private synthesis from alone time.
"""


@dataclass(frozen=True)
class PersonContext:
    root: Path

    @classmethod
    def create(cls, root: str | Path, *, overwrite: bool = False) -> "PersonContext":
        context = cls(Path(root))
        context.root.mkdir(parents=True, exist_ok=True)
        context._write_template("character.md", CHARACTER_TEMPLATE, overwrite=overwrite)
        context._write_template("you.md", YOU_TEMPLATE, overwrite=overwrite)
        context._write_template("recent.md", RECENT_TEMPLATE, overwrite=overwrite)
        context._write_template("reflections.md", REFLECTIONS_TEMPLATE, overwrite=overwrite)
        return context

    @classmethod
    def load(cls, root: str | Path) -> "PersonContext":
        context = cls(Path(root))
        missing = [
            path.name
            for path in context.required_files()
            if not path.exists()
        ]
        if missing:
            joined = ", ".join(missing)
            raise FileNotFoundError(f"person context is missing: {joined}")
        return context

    @property
    def character_path(self) -> Path:
        return self.root / "character.md"

    @property
    def you_path(self) -> Path:
        return self.root / "you.md"

    @property
    def recent_path(self) -> Path:
        return self.root / "recent.md"

    @property
    def reflections_path(self) -> Path:
        return self.root / "reflections.md"

    @property
    def archive_path(self) -> Path:
        return self.root / "archive.sqlite"

    def required_files(self) -> tuple[Path, Path, Path, Path]:
        return (
            self.character_path,
            self.you_path,
            self.recent_path,
            self.reflections_path,
        )

    def read_character(self) -> str:
        return self.character_path.read_text(encoding="utf-8").strip()

    def read_you(self) -> str:
        return self.you_path.read_text(encoding="utf-8").strip()

    def read_recent(self) -> str:
        return self.recent_path.read_text(encoding="utf-8").strip()

    def read_reflections(self) -> str:
        return self.reflections_path.read_text(encoding="utf-8").strip()

    def append_recent(self, text: str) -> None:
        self._append(self.recent_path, text)

    def append_reflection(self, text: str) -> None:
        self._append(self.reflections_path, text)

    def _write_template(self, name: str, content: str, *, overwrite: bool) -> None:
        path = self.root / name
        if path.exists() and not overwrite:
            return
        path.write_text(content.rstrip() + "\n", encoding="utf-8")

    def _append(self, path: Path, text: str) -> None:
        normalized = text.strip()
        if not normalized:
            return
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        separator = "\n\n" if current.strip() else ""
        path.write_text(current.rstrip() + separator + normalized + "\n", encoding="utf-8")
