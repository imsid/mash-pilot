"""The Pilot catalog: every pooled agent the store ships, with its listing.

Each entry pairs an agent factory with the `AgentMetadata` that becomes its
store listing (and, when the agent serves as a subagent, the delegation
directory the primary reads). Adding an agent to the store is adding a
package under this directory and one entry to `CATALOG`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

# Load the repo .env before any agent module is imported: agent modules read
# model/provider configuration from the environment at import time.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from mash.runtime import AgentMetadata, AgentSpec  # noqa: E402

from . import mash_guide  # noqa: E402
from .mash_guide import api, cli, mcp, runtime, workflow  # noqa: E402
from .personal import finance_watch, morning_brief  # noqa: E402
from .workflows import quiz  # noqa: E402


@dataclass(frozen=True)
class CatalogEntry:
    """One store listing: an agent id, its spec factory, and its metadata."""

    agent_id: str
    create_spec: Callable[..., AgentSpec]  # accepts workspace_root=...
    build_metadata: Callable[[], AgentMetadata]


CATALOG: tuple[CatalogEntry, ...] = (
    CatalogEntry(
        mash_guide.MASH_GUIDE_AGENT_ID,
        mash_guide.create_spec,
        mash_guide.build_metadata,
    ),
    CatalogEntry(
        cli.CLI_COPILOT_AGENT_ID,
        cli.create_cli_copilot_spec,
        cli.build_cli_metadata,
    ),
    CatalogEntry(
        api.API_COPILOT_AGENT_ID,
        api.create_api_copilot_spec,
        api.build_api_metadata,
    ),
    CatalogEntry(
        mcp.MCP_COPILOT_AGENT_ID,
        mcp.create_mcp_copilot_spec,
        mcp.build_mcp_metadata,
    ),
    CatalogEntry(
        runtime.RUNTIME_COPILOT_AGENT_ID,
        runtime.create_runtime_copilot_spec,
        runtime.build_runtime_metadata,
    ),
    CatalogEntry(
        workflow.WORKFLOW_COPILOT_AGENT_ID,
        workflow.create_workflow_copilot_spec,
        workflow.build_workflow_metadata,
    ),
    CatalogEntry(
        morning_brief.MORNING_BRIEF_AGENT_ID,
        morning_brief.create_spec,
        morning_brief.build_metadata,
    ),
    CatalogEntry(
        finance_watch.FINANCE_WATCH_AGENT_ID,
        finance_watch.create_spec,
        finance_watch.build_metadata,
    ),
    CatalogEntry(
        quiz.QUIZ_AGENT_ID,
        quiz.create_spec,
        quiz.build_metadata,
    ),
)

__all__ = ["CATALOG", "CatalogEntry"]
