from __future__ import annotations

import argparse
from pathlib import Path

from memory_agent.agent import MemoryAugmentedAgent
from memory_agent.composer import ContextComposer
from memory_agent.curator import MemoryCurator
from memory_agent.person import PersonContext
from memory_agent.store import MemoryStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="memory-agent")
    parser.add_argument("--db", help="SQLite memory DB path")
    parser.add_argument("--namespace", default="default", help="Memory namespace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    remember_parser = subparsers.add_parser("remember")
    remember_parser.add_argument("content")
    remember_parser.add_argument("--kind", default="observation")
    remember_parser.add_argument("--summary")
    remember_parser.add_argument("--importance", type=float, default=0.5)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=5)

    ask_parser = subparsers.add_parser("ask")
    ask_parser.add_argument("message")

    init_person_parser = subparsers.add_parser("init-person")
    init_person_parser.add_argument("path")
    init_person_parser.add_argument("--overwrite", action="store_true")

    reflect_parser = subparsers.add_parser("reflect")
    reflect_parser.add_argument("person_path")
    reflect_parser.add_argument("transcript_path")
    reflect_parser.add_argument("--limit", type=int, default=8)

    context_parser = subparsers.add_parser("context")
    context_parser.add_argument("person_path")
    context_parser.add_argument("query")
    context_parser.add_argument("--limit", type=int, default=6)

    args = parser.parse_args()
    if args.command == "init-person":
        person = PersonContext.create(args.path, overwrite=args.overwrite)
        print(person.root)
        return

    person = _person_for_args(args)
    store = _store_for_args(args, person)
    try:
        if args.command == "remember":
            memory = store.remember(
                args.content,
                namespace=args.namespace,
                kind=args.kind,
                summary=args.summary,
                importance=args.importance,
            )
            print(memory.id)
        elif args.command == "search":
            for result in store.search(
                args.query,
                namespace=args.namespace,
                limit=args.limit,
            ):
                print(f"{result.score:.3f}\t{result.memory.kind}\t{result.memory.summary}")
        elif args.command == "ask":
            print(MemoryAugmentedAgent(store, namespace=args.namespace).run(args.message))
        elif args.command == "reflect":
            if person is None:
                raise RuntimeError("reflect requires a person context")
            transcript = Path(args.transcript_path).read_text(encoding="utf-8")
            memories = MemoryCurator().persist(
                transcript,
                person=person,
                store=store,
                namespace=args.namespace,
                limit=args.limit,
            )
            for memory in memories:
                print(f"{memory.importance:.2f}\t{memory.kind.value}\t{memory.summary}")
        elif args.command == "context":
            if person is None:
                raise RuntimeError("context requires a person context")
            print(
                ContextComposer(
                    person,
                    store,
                    namespace=args.namespace,
                    memory_limit=args.limit,
                ).compose(args.query)
            )
    finally:
        store.close()


def _person_for_args(args: argparse.Namespace) -> PersonContext | None:
    if args.command in {"reflect", "context"}:
        return PersonContext.load(args.person_path)
    return None


def _store_for_args(args: argparse.Namespace, person: PersonContext | None) -> MemoryStore:
    if args.db:
        return MemoryStore(Path(args.db))
    if person is not None:
        return MemoryStore(person.archive_path)
    return MemoryStore(Path(".memory.sqlite"))


if __name__ == "__main__":
    main()
