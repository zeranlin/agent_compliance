from __future__ import annotations

import argparse
from typing import Callable


def register_web_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    handlers: dict[str, Callable[[argparse.Namespace], int]],
) -> None:
    web_parser = subparsers.add_parser(
        "web",
        help="Run local review web UI",
        description="Run local review web UI",
    )
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--port", type=int, default=8765)
    handlers["web"] = handle_web


def handle_web(args: argparse.Namespace) -> int:
    from agent_compliance.apps.web.app import run_web_server

    run_web_server(host=args.host, port=args.port)
    return 0
