from __future__ import annotations

import argparse
from typing import Callable

from agent_compliance.apps.commands import (
    register_incubator_commands,
    register_review_commands,
    register_web_commands,
)


CommandHandler = Callable[[argparse.Namespace], int]


def build_parser() -> argparse.ArgumentParser:
    parser, _ = _build_parser_and_handlers()
    return parser


def _build_parser_and_handlers() -> tuple[argparse.ArgumentParser, dict[str, CommandHandler]]:
    parser = argparse.ArgumentParser(prog="agent-compliance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    handlers: dict[str, CommandHandler] = {}

    register_review_commands(subparsers, handlers)
    register_incubator_commands(subparsers, handlers)
    register_web_commands(subparsers, handlers)
    return parser, handlers


def main(argv: list[str] | None = None) -> int:
    parser, handlers = _build_parser_and_handlers()
    args = parser.parse_args(argv)
    handler = handlers.get(args.command)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
        return 2
    return handler(args)
