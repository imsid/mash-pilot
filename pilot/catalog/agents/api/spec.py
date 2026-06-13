"""API copilot agent spec."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mash.core.config import AgentConfig
from mash.runtime import AgentMetadata
from mash.tools.bash import BashTool
from mash.tools.registry import ToolRegistry

from ..._base import CopilotAgentSpec

API_COPILOT_AGENT_ID = "api-copilot"
API_DOC_ROOTS = ("src/mash/api",)


class ApiCopilotSpec(CopilotAgentSpec):
    """Subagent specialized in the Mash API codepath."""

    def get_agent_id(self) -> str:
        return API_COPILOT_AGENT_ID

    def build_tools(self) -> ToolRegistry:
        tools = ToolRegistry()
        tools.register(BashTool(working_dir=str(self.workspace_root)))
        return tools

    def build_system_prompt(self) -> list[dict[str, Any]]:
        return self._build_copilot_prompt_blocks(
            scope="src/mash/api",
            doc_roots=API_DOC_ROOTS,
            cache_label="API",
        )

    def build_agent_config(self) -> AgentConfig:
        return self._build_copilot_config(API_COPILOT_AGENT_ID)


def build_api_metadata() -> AgentMetadata:
    return AgentMetadata(
        display_name="Mash API Copilot",
        description=(
            "Specialist for the Mash hosted API surface, FastAPI app wiring, host "
            "serving entrypoints, telemetry API endpoints, and telemetry UI integration."
        ),
        capabilities=[
            "src/mash/api",
            "host api",
            "telemetry ui",
            "fastapi app wiring",
            "host serving",
            "api configuration",
            "telemetry API endpoints",
            "/telemetry/traces",
            "/telemetry/trace/analysis",
            "/telemetry/events",
            "/telemetry/events/stream",
            "/telemetry/memory/search",
        ],
        usage_guidance=(
            "Use for questions centered on the API app, host startup, HTTP-facing "
            "configuration, telemetry UI assets, telemetry API endpoints "
            "(traces, trace analysis, events, event streaming, memory search), "
            "or other behavior implemented under `src/mash/api`."
        ),
    )


def create_api_copilot_spec(*, workspace_root: str) -> ApiCopilotSpec:
    return ApiCopilotSpec(Path(workspace_root).resolve())
