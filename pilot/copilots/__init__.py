"""Copilot agent specs for the Mash Pilot host."""

from .api import ApiCopilotSpec, build_api_metadata, create_api_copilot_spec
from .cli import CliCopilotSpec, build_cli_metadata, create_cli_copilot_spec
from .mcp import McpCopilotSpec, build_mcp_metadata, create_mcp_copilot_spec
from .runtime import (
    RuntimeCopilotSpec,
    build_runtime_metadata,
    create_runtime_copilot_spec,
)
from .workflow import (
    WorkflowCopilotSpec,
    build_workflow_metadata,
    create_workflow_copilot_spec,
)

__all__ = [
    "ApiCopilotSpec",
    "CliCopilotSpec",
    "McpCopilotSpec",
    "RuntimeCopilotSpec",
    "WorkflowCopilotSpec",
    "build_api_metadata",
    "build_cli_metadata",
    "build_mcp_metadata",
    "build_runtime_metadata",
    "build_workflow_metadata",
    "create_api_copilot_spec",
    "create_cli_copilot_spec",
    "create_mcp_copilot_spec",
    "create_runtime_copilot_spec",
    "create_workflow_copilot_spec",
]
