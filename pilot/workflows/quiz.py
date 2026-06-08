"""Pilot quiz workflow agent and REPL command."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

from mash.cli.commands import Command
from mash.core.config import AgentConfig
from mash.core.llm import LLMProvider
from mash.core.llm.anthropic import AnthropicProvider
from mash.core.llm.openai import OpenAIProvider
from mash.runtime.spec import AgentSpec
from mash.skills.base import Skill
from mash.skills.registry import SkillRegistry
from mash.tools.ask_user import AskUserTool
from mash.tools.bash import BashTool
from mash.tools.registry import ToolRegistry
from mash.workflows import TaskSpec, WorkflowSpec

from ..prompt import build_repo_context

QUIZ_AGENT_ID = "quiz-me"
QUIZ_WORKFLOW_ID = "pilot-quiz"
QUIZ_TASK_ID = "run-quiz"
QUIZ_SKILL_NAME = "mash-quiz"
QUIZ_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

QUIZ_DOC_ROOTS = (
    "src/mash/core",
    "src/mash/tools",
    "src/mash/skills",
    "src/mash/runtime",
    "src/mash/workflows",
    "src/mash/mcp",
    "src/mash/cli",
    "src/mash/api",
    "src/mash/agents/masher",
)
QUIZ_EXTRA_DOC_PATHS = (
    "README.md",
    "HOW_TO_DEPLOY.md",
    "src/mash/AGENTS.md",
    "docs/rfcs/host-to-agent-protocol.md",
)

_PROMPT = """You are a Mash quiz workflow worker.

You are invoked only by the pilot-quiz workflow. Do not answer free-form chat.

Every request is JSON with workflow_id, workflow_run_id, task_id, workflow_input,
and task_state.

Workflow skill routing:
- workflow_id=pilot-quiz, task_id=run-quiz -> skill=mash-quiz

Routing rules:
- Match both workflow_id and task_id exactly.
- Call the standard Skill tool exactly once with the matched skill name before doing workflow work.
- After the skill loads, follow only the loaded skill's workflow instructions.
- If no route matches, return an error object and do not call workflow tools.

Use the cached docs below as your primary knowledge source for generating
quiz questions. They cover every major Mash module. Use Bash only for narrow
verification or to look up specific implementation details.
"""


def _quiz_cached_doc_paths(
    workspace_root: Path,
    *,
    doc_roots: Sequence[str] = (),
    extra_doc_paths: Sequence[str] = (),
) -> list[str]:
    doc_paths: list[str] = []
    seen: set[str] = set()
    for root in doc_roots:
        root_path = (workspace_root / root).resolve()
        for filename in ("README.md", "AGENTS.md"):
            candidate = root_path / filename
            if candidate.is_file():
                resolved = str(candidate)
                if resolved not in seen:
                    seen.add(resolved)
                    doc_paths.append(resolved)
    for relpath in extra_doc_paths:
        candidate = (workspace_root / relpath).resolve()
        if candidate.is_file():
            resolved = str(candidate)
            if resolved not in seen:
                seen.add(resolved)
                doc_paths.append(resolved)
    return doc_paths


class QuizAgentSpec(AgentSpec):
    """Workflow agent for interactive Mash quizzes."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def get_agent_id(self) -> str:
        return QUIZ_AGENT_ID

    def build_tools(self) -> ToolRegistry:
        tools = ToolRegistry()
        tools.register(AskUserTool())
        tools.register(BashTool(working_dir=str(self.workspace_root)))
        return tools

    def build_skills(self) -> SkillRegistry:
        skills = SkillRegistry()
        skill_dir = QUIZ_SKILLS_DIR / "mash-quiz"
        skills.register(
            Skill(
                type="custom",
                name=QUIZ_SKILL_NAME,
                description="Interactive quiz about Mash SDK internals for learning.",
                location=str(skill_dir),
            )
        )
        return skills

    def build_llm(self) -> LLMProvider:
        if os.getenv("ANTHROPIC_API_KEY", "").strip():
            return AnthropicProvider(
                app_id=QUIZ_AGENT_ID,
                model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            )
        if os.getenv("OPENAI_API_KEY", "").strip():
            return OpenAIProvider(
                app_id=QUIZ_AGENT_ID,
                model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            )
        raise RuntimeError("Quiz agent requires ANTHROPIC_API_KEY or OPENAI_API_KEY.")

    def build_system_prompt(self) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": _PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        repo_context = build_repo_context(
            repo=str(self.workspace_root),
            cached_files=_quiz_cached_doc_paths(
                self.workspace_root,
                doc_roots=QUIZ_DOC_ROOTS,
                extra_doc_paths=QUIZ_EXTRA_DOC_PATHS,
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
            app_id=QUIZ_AGENT_ID,
            system_prompt=self.build_system_prompt(),
            skills_enabled=True,
            max_steps=30,
        )

    def enable_runtime_tools(self) -> bool:
        return False


def build_quiz_workflow_spec(quiz_spec: QuizAgentSpec) -> WorkflowSpec:
    return WorkflowSpec(
        workflow_id=QUIZ_WORKFLOW_ID,
        tasks=[
            TaskSpec(
                task_id=QUIZ_TASK_ID,
                agent_spec=quiz_spec,
            )
        ],
        metadata={"source": "pilot", "kind": "quiz"},
    )


def register_quiz_command(shell: Any) -> None:
    """Register Pilot's quiz workflow command on a Mash shell."""

    def quiz_command(ctx: Any, args: list[str]) -> None:
        if args:
            ctx.renderer.error("Usage: /quiz")
            return

        run = ctx.client.run_workflow(QUIZ_WORKFLOW_ID)
        ctx.renderer.info(f"Workflow: {run.get('workflow_id') or QUIZ_WORKFLOW_ID}")
        run_id = str(run.get("run_id") or "")
        ctx.renderer.info(f"Run ID: {run_id}")
        if not run_id:
            ctx.renderer.info(f"Status: {run.get('status') or ''}")
            return

        streamed_response_text: str | None = None
        try:
            for event in ctx.client.stream_workflow_run(QUIZ_WORKFLOW_ID, run_id):
                event_name = str(event.get("event") or "")
                payload = event.get("data")
                if not isinstance(payload, dict):
                    continue

                task_agent_id = str(payload.get("task_agent_id") or "")

                if event_name == "agent.trace":
                    shell.render_runtime_trace_payload(
                        payload,
                        trace_label="Quiz",
                        agent_id=task_agent_id or None,
                    )
                    if task_agent_id:
                        streamed_text = shell.extract_streamed_response_text(
                            payload,
                            agent_id=task_agent_id,
                        )
                        if streamed_text:
                            streamed_response_text = streamed_text
                    continue

                if event_name == "request.interaction.create":
                    shell.chain_renderer.finish_trace()
                    _handle_quiz_interaction(ctx, payload)
                    continue

                if event_name == "request.interaction.ack":
                    _render_interaction_ack(ctx, payload)
                    continue

                if event_name == "request.completed":
                    shell.chain_renderer.finish_trace()
                    response_payload = payload.get("response")
                    if isinstance(response_payload, dict):
                        text = str(response_payload.get("text") or "")
                    else:
                        text = str(payload.get("text") or "")
                    if text and text != streamed_response_text:
                        ctx.renderer.markdown(text)
                    break

                if event_name == "request.error":
                    error = payload.get("error")
                    raise RuntimeError(str(error or "quiz workflow request failed"))

                if event_name == "workflow.error":
                    error = payload.get("error")
                    raise RuntimeError(str(error or "quiz workflow failed"))
        finally:
            shell.chain_renderer.finish_trace()

    shell.register_command(
        Command(
            name="quiz",
            help="Interactive quiz about Mash internals",
            handler=quiz_command,
        )
    )


def _handle_quiz_interaction(ctx: Any, payload: dict[str, Any]) -> None:
    """Present an AskUser interaction to the user and post the response."""
    interaction_id = str(payload.get("interaction_id") or "")
    interaction_type = str(payload.get("type") or "info")
    prompt = str(payload.get("prompt") or "Input required:")
    schema = payload.get("schema")
    agent_id = str(payload.get("agent_id") or payload.get("task_agent_id") or "")
    request_id = str(payload.get("request_id") or "")

    ctx.renderer.info(f"\n{prompt}")

    if interaction_type == "choice":
        options: list[str] = []
        if isinstance(schema, dict):
            options = schema.get("options", [])
        for i, opt in enumerate(options, 1):
            ctx.renderer.info(f"  {i}. {opt}")
        ctx.renderer.info("  Enter numbers separated by commas:")
        user_input = input("  > ").strip()
        selected: list[str] = []
        for part in user_input.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(options):
                    selected.append(options[idx])
                elif part in options:
                    selected.append(part)
        response: Any = selected
    else:
        response = input("  > ").strip()

    ctx.client.post_interaction(
        agent_id,
        request_id,
        interaction_id=interaction_id,
        response=response,
    )


def _render_interaction_ack(ctx: Any, payload: dict[str, Any]) -> None:
    """Render an interaction acknowledgement."""
    timed_out = payload.get("timed_out", False)
    if timed_out:
        interaction_id = str(payload.get("interaction_id") or "")
        ctx.renderer.warn(f"  Interaction {interaction_id} timed out")
