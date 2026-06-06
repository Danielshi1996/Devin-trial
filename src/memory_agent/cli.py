from __future__ import annotations

import argparse
from pathlib import Path

from memory_agent.agent import MemoryAugmentedAgent
from memory_agent.store import MemoryStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="memory-agent")
    parser.add_argument("--db", default=".memory.sqlite", help="SQLite memory DB path")
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

    args = parser.parse_args()
    store = MemoryStore(Path(args.db))
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
    finally:
        store.close()


if __name__ == "__main__":
    main()
