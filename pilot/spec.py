"""Pilot pool assembly: register the catalog as a flat pool.

No hosts are defined here. Compositions are configuration, owned by the
CLI's host config file (`pilot.store`) and published over the control API.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Sequence

from mash.api import MashHostConfig, run_host
from mash.runtime import AgentPool, HostBuilder

from .catalog import CATALOG
from .catalog.workflows.quiz import build_quiz_workflow_spec


def build_pool(workspace_root: Path | None = None) -> AgentPool:
    """Build the Pilot agent pool from the catalog. The pool ships no host
    compositions; workflow definitions are registered so host configs can
    reference them by id (e.g. `workflows: ["pilot-quiz"]`)."""
    resolved_workspace_root = (
        workspace_root or Path(os.environ.get("PILOT_WORKSPACE_ROOT", "."))
    ).resolve()
    ws = str(resolved_workspace_root)

    builder = HostBuilder()
    for entry in CATALOG:
        builder.agent(
            entry.create_spec(workspace_root=ws), metadata=entry.build_metadata()
        )
    builder.enable_masher()
    pool = builder.build()

    pool.register_workflow(build_quiz_workflow_spec())
    return pool


# Back-compat alias: existing deployments may still point MASH_HOST_APP at
# `pilot.spec:build_host`. Drop once they are confirmed on `build_pool`.
build_host = build_pool


def serve(
    *,
    workspace_root: str = ".",
    bind_host: str = "127.0.0.1",
    bind_port: int = 8000,
    api_key: str | None = None,
) -> int:
    """Run the Pilot host API over the pool. Blocks until shutdown."""
    run_host(
        build_pool(Path(workspace_root).resolve()),
        config=MashHostConfig(
            bind_host=bind_host,
            bind_port=bind_port,
            api_key=api_key,
        ),
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Mash Pilot host over the Mash host API."
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace folder exposed to the Mash pilot subagents.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="API bind host.")
    parser.add_argument("--port", type=int, default=8000, help="API bind port.")
    parser.add_argument("--api-key", default=None, help="Optional API key.")
    args = parser.parse_args(argv)

    return serve(
        workspace_root=args.workspace_root,
        bind_host=args.host,
        bind_port=args.port,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    raise SystemExit(main())
