"""Pilot CLI — standalone client for the Mash Pilot host."""

from __future__ import annotations

import argparse
import os
from typing import Sequence

from mash.cli.client import MashHostClient
from mash.cli.render import RichRenderer
from mash.cli.shell import MashRemoteShell, ShellTarget

from .workflows.changelog import register_changelog_command
from .workflows.quiz import register_quiz_command

PILOT_DEFAULT_API_BASE_URL = os.environ.get(
    "PILOT_API_BASE_URL",
    "https://pilot-tk3b.onrender.com",
)
PILOT_HOST_ID = "pilot"


def _resolve_connection(args: argparse.Namespace) -> tuple[str, str | None, str | None]:
    base_url = (
        args.api_base_url
        or os.environ.get("MASH_API_BASE_URL")
        or PILOT_DEFAULT_API_BASE_URL
    ).strip()
    api_key = args.api_key or os.environ.get("MASH_API_KEY") or None
    agent_id = args.agent
    if not base_url:
        raise ValueError(
            "API base URL is required. Use --api-base-url or PILOT_API_BASE_URL."
        )
    return base_url, api_key, agent_id


def _resolve_target(
    client: MashHostClient, explicit_agent: str | None
) -> tuple[str, str | None]:
    """Resolve (agent_id, host_id) for the shell target.

    With --agent the shell runs in bare-agent mode (no host, no delegation);
    otherwise it targets the code-defined `pilot` host composition.
    """
    if explicit_agent:
        return explicit_agent, None
    try:
        described = client.get_host(PILOT_HOST_ID)
    except Exception as exc:
        raise ValueError(
            f"host '{PILOT_HOST_ID}' is not defined on this deployment "
            f"(expected it from pilot.spec:build_pool): {exc}"
        ) from exc
    primary = described.get("primary") or {}
    agent_id = primary.get("agent_id") if isinstance(primary, dict) else None
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError(
            f"host '{PILOT_HOST_ID}' did not report a primary agent id"
        )
    return agent_id.strip(), PILOT_HOST_ID


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pilot",
        description="Pilot CLI — talk to the Mash Pilot host.",
    )
    parser.add_argument("--api-base-url", default=None, help="Mash host base URL")
    parser.add_argument("--api-key", default=None, help="Bearer API key")
    parser.add_argument(
        "--agent",
        default=None,
        help="Target a single agent directly (bare-agent mode, no delegation)",
    )
    subparsers = parser.add_subparsers(dest="command")

    repl = subparsers.add_parser("repl", help="Start a Pilot remote REPL")
    repl.add_argument("--session-id", default=None, help="Remote session id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    renderer = RichRenderer()

    try:
        if args.command == "repl":
            base_url, api_key, configured_agent = _resolve_connection(args)
            client = MashHostClient(base_url, api_key=api_key)
            try:
                agent_id, host_id = _resolve_target(client, configured_agent)
                target = ShellTarget(
                    api_base_url=base_url,
                    agent_id=agent_id,
                    session_id=args.session_id or MashRemoteShell.new_session_id(),
                    host_id=host_id,
                )
                shell = MashRemoteShell(client, target)
                register_changelog_command(shell)
                register_quiz_command(shell)
                shell.run()
                return 0
            finally:
                client.close()
    except Exception as exc:
        renderer.error(str(exc))
        return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
