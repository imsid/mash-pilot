"""Pilot agent specs and pool registration."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv
from mash.api import MashHostConfig, run_host
from mash.core.config import AgentConfig
from mash.core.llm import LLMProvider
from mash.core.llm.anthropic import AnthropicProvider
from mash.mcp.types import MCPServerConfig
from mash.runtime import AgentMetadata, AgentPool, AgentSpec, Host, HostBuilder
from mash.skills.registry import SkillRegistry
from mash.tools.ask_user import AskUserTool
from mash.tools.bash import BashTool
from mash.tools.registry import ToolRegistry

from .copilots import (
    build_api_metadata,
    build_cli_metadata,
    build_mcp_metadata,
    build_runtime_metadata,
    build_workflow_metadata,
    create_api_copilot_spec,
    create_cli_copilot_spec,
    create_mcp_copilot_spec,
    create_runtime_copilot_spec,
    create_workflow_copilot_spec,
)
from .copilots._base import APP_NAME, scope_doc_paths
from .copilots.api import API_COPILOT_AGENT_ID
from .copilots.cli import CLI_COPILOT_AGENT_ID
from .copilots.mcp import MCP_COPILOT_AGENT_ID
from .copilots.runtime import RUNTIME_COPILOT_AGENT_ID
from .copilots.workflow import WORKFLOW_COPILOT_AGENT_ID
from .prompt import build_base_prompt, build_repo_context
from .tools import UpdateDocsTool
from .workflows.quiz import QuizAgentSpec, build_quiz_workflow_spec

PILOT_AGENT_ID = "pilot"
PILOT_HOST_ID = "pilot"
DEFAULT_SUBAGENT_TIMEOUT_MS = 360_000

PILOT_DOC_ROOTS = (
    "src/mash/core",
    "src/mash/tools",
    "src/mash/skills",
    "src/mash/logging",
    "src/mash/memory",
    "src/mash/agents/masher",
)
PILOT_EXTRA_DOC_PATHS = (
    "README.md",
    "src/mash/README.md",
    "docs/posts/product-brief.md",
    "docs/posts/building-agent-clis.md",
    "docs/posts/building-dynamic-hosts-apis.md",
    "docs/posts/how-to-deploy.md",
    "docs/rfcs/host-to-agent-protocol.md",
)


def _load_pilot_env() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")


_load_pilot_env()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL") or "https://api.githubcopilot.com/mcp/"
GITHUB_MCP_PAT = os.getenv("GITHUB_MCP_PAT")
GITHUB_MCP_CONNECTION_NAME = "github"

PILOT_SKILLS_DIR = Path(__file__).resolve().parent / "skills"


class PilotSpec(AgentSpec):
    """Primary pilot specialized in Mash codebase."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def get_agent_id(self) -> str:
        return PILOT_AGENT_ID

    def build_tools(self) -> ToolRegistry:
        tools = ToolRegistry()
        tools.register(BashTool(working_dir=str(self.workspace_root)))
        tools.register(UpdateDocsTool(workspace_root=str(self.workspace_root)))
        tools.register(AskUserTool())
        return tools

    def build_llm(self) -> LLMProvider:
        return AnthropicProvider(
            app_id=self.get_agent_id(),
            model=ANTHROPIC_MODEL,
            api_key=ANTHROPIC_API_KEY,
        )

    def build_mcp_servers(self) -> list[MCPServerConfig]:
        github_mcp_url = os.getenv("GITHUB_MCP_URL") or GITHUB_MCP_URL
        github_mcp_pat = os.getenv("GITHUB_MCP_PAT") or GITHUB_MCP_PAT
        if not github_mcp_url or not github_mcp_pat:
            return []
        return [
            MCPServerConfig(
                name=GITHUB_MCP_CONNECTION_NAME,
                url=github_mcp_url,
                description="GitHub MCP server for mashpy repository inspection",
                headers={"Authorization": f"Bearer {github_mcp_pat}"},
                allowed_tools=[
                    "list_commits",
                    "get_commit",
                ],
            )
        ]

    def build_skills(self) -> SkillRegistry:
        registry = SkillRegistry()
        for skill in registry.get_custom_skills(PILOT_SKILLS_DIR):
            registry.register(skill)
        return registry

    def build_system_prompt(self) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": "\n".join(
                    [
                        build_base_prompt(
                            repo=str(self.workspace_root),
                            role=f"You are the primary Mash codebase guide in {APP_NAME}.",
                            extra_rules=(
                                "Handle shared and core questions for `src/mash/core`, `src/mash/tools`, `src/mash/skills`, `src/mash/logging`, `src/mash/memory`, and other cross-cutting codebase behavior.",
                                f"Delegate to `{CLI_COPILOT_AGENT_ID}`, `{API_COPILOT_AGENT_ID}`, `{MCP_COPILOT_AGENT_ID}`, `{RUNTIME_COPILOT_AGENT_ID}`, or `{WORKFLOW_COPILOT_AGENT_ID}` when the question is centered on that module.",
                                "Return one synthesized answer after any delegation.",
                                "If a subagent call fails or returns an incomplete answer, do not repeat the same delegation blindly; use your own cached docs and one targeted bash lookup to finish the answer when possible.",
                                "For observability, telemetry, trace analysis, or span questions: delegate data model and analysis questions (spans, TraceAnalysis, timing breakdowns, tool stats) to `runtime-copilot`, API endpoint questions (/telemetry/traces, /telemetry/trace/analysis, event streaming) to `api-copilot`, CLI rendering questions (/trace command, chain_renderer, subagent trace rendering) to `cli-copilot`. For cross-cutting observability questions, prefer `runtime-copilot` as the primary delegate.",
                                "If you need direct code verification, use one targeted bash command and answer directly.",
                                f"Default delegated opts.timeout_ms={DEFAULT_SUBAGENT_TIMEOUT_MS}.",
                                "Include the working folder in delegated prompts unless the user says otherwise:",
                                f"'Working folder: {self.workspace_root}'",
                            ),
                        ),
                    ]
                ),
                "cache_control": {"type": "ephemeral"},
            }
        ]
        repo_context = build_repo_context(
            repo=str(self.workspace_root),
            cached_files=scope_doc_paths(
                self.workspace_root,
                doc_roots=PILOT_DOC_ROOTS,
                extra_doc_paths=PILOT_EXTRA_DOC_PATHS,
            ),
        )
        if repo_context:
            blocks.append(
                {
                    "type": "text",
                    "text": repo_context,
                    "cache_control": {"type": "ephemeral"},
                }
            )
        return blocks

    def build_agent_config(self) -> AgentConfig:
        return AgentConfig(
            app_id=PILOT_AGENT_ID,
            system_prompt=self.build_system_prompt(),
            skills_enabled=True,
            temperature=0.2,
        )


def create_pilot_spec(*, workspace_root: str) -> PilotSpec:
    return PilotSpec(Path(workspace_root).resolve())


def build_pilot_metadata() -> AgentMetadata:
    return AgentMetadata(
        display_name="Pilot",
        description=(
            "Primary Mash codebase guide; handles core, tools, skills, logging, "
            "memory, and cross-cutting questions."
        ),
        capabilities=[
            "src/mash/core",
            "src/mash/tools",
            "src/mash/skills",
            "src/mash/logging",
            "src/mash/memory",
            "cross-cutting codebase questions",
            "answer synthesis across modules",
        ],
        usage_guidance=(
            "Default entry point for Mash codebase questions. Use for shared and "
            "core behavior, or questions that span multiple modules; module-"
            "centered questions belong to the matching copilot."
        ),
    )


def build_pool(workspace_root: Path | None = None) -> AgentPool:
    """Build the Mash Pilot agent pool plus the `pilot` host composition."""
    resolved_workspace_root = (
        workspace_root or Path(os.environ.get("PILOT_WORKSPACE_ROOT", "."))
    ).resolve()
    ws = str(resolved_workspace_root)
    pool = (
        HostBuilder()
        .agent(create_pilot_spec(workspace_root=ws), metadata=build_pilot_metadata())
        .agent(
            create_cli_copilot_spec(workspace_root=ws), metadata=build_cli_metadata()
        )
        .agent(
            create_api_copilot_spec(workspace_root=ws), metadata=build_api_metadata()
        )
        .agent(
            create_mcp_copilot_spec(workspace_root=ws), metadata=build_mcp_metadata()
        )
        .agent(
            create_runtime_copilot_spec(workspace_root=ws),
            metadata=build_runtime_metadata(),
        )
        .agent(
            create_workflow_copilot_spec(workspace_root=ws),
            metadata=build_workflow_metadata(),
        )
        .enable_masher()
        .host(
            Host(
                host_id=PILOT_HOST_ID,
                primary=PILOT_AGENT_ID,
                subagents=(
                    CLI_COPILOT_AGENT_ID,
                    API_COPILOT_AGENT_ID,
                    MCP_COPILOT_AGENT_ID,
                    RUNTIME_COPILOT_AGENT_ID,
                    WORKFLOW_COPILOT_AGENT_ID,
                ),
            )
        )
        .build()
    )
    quiz_spec = QuizAgentSpec(workspace_root=resolved_workspace_root)
    pool.register_workflow_agent(quiz_spec)
    pool.register_workflow(build_quiz_workflow_spec(quiz_spec))
    return pool


# Back-compat alias: existing deployments may still point MASH_HOST_APP at
# `pilot.spec:build_host`. Drop once they are confirmed on `build_pool`.
build_host = build_pool


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

    run_host(
        build_pool(Path(args.workspace_root).resolve()),
        config=MashHostConfig(
            bind_host=args.host,
            bind_port=args.port,
            api_key=args.api_key,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
