# Pilot README

`pilot/` defines the Mash Pilot host: one primary codebase guide plus focused module copilots.

## What Is Pilot?

Pilot is a multi-agent Mash application that demonstrates:
- **Primary agent delegation**: the `pilot` agent handles shared/cross-cutting questions and delegates to specialized copilots
- **Tool approval gating**: the `UpdateDocsTool` demonstrates `requires_approval` for durable user consent
- **Durable user interactions**: the `AskUserTool` shows how agents can ask questions and wait for responses across runtime restarts
- **Dynamic skills**: the `/changelog` REPL command dynamically publishes a skill and workflow on first use
- **Workflow-only agents**: Masher workflows are hidden from subagent listings but callable from workflow tasks

## Agent Layout

### Primary Agent
- **`pilot`**: primary guide for shared and cross-cutting codebase questions. Owns questions about `src/mash/core`, `src/mash/tools`, `src/mash/skills`, `src/mash/logging`, `src/mash/memory`, and general system architecture.

### Module Copilots (Subagents)
- **`cli-copilot`**: specialist for `src/mash/cli` — CLI commands, REPL behavior, terminal rendering, command dispatch, and session routing
- **`api-copilot`**: specialist for `src/mash/api` — HTTP API, FastAPI wiring, host serving, telemetry UI, and API configuration
- **`mcp-copilot`**: specialist for `src/mash/mcp` — MCP client/server wiring, manager configuration, transport details, and tool adaptation
- **`runtime-copilot`**: specialist for `src/mash/runtime` — agent runtime, host composition, request handling, event sourcing, and durable workflow execution
- **`workflow-copilot`**: specialist for `src/mash/workflows` — workflow specs, registry, DBOS orchestration, run status, and task state handoff

### Workflow-Only Agents (Not Subagents)
- **`masher-trace-digest`**: built-in workflow-only agent for trace digest generation. Not exposed as a subagent; only callable from workflow tasks.
- **`masher-online-eval-curation`**: built-in workflow-only agent for online eval curation. Not exposed as a subagent; only callable from workflow tasks.

## Delegation Strategy

The primary pilot automatically delegates questions to the appropriate copilot:

- **CLI questions** (commands, REPL, terminal rendering) → `cli-copilot`
- **API questions** (HTTP routes, FastAPI, telemetry UI) → `api-copilot`
- **MCP questions** (servers, clients, tool adaptation) → `mcp-copilot`
- **Runtime questions** (request lifecycle, event sourcing, durability) → `runtime-copilot`
- **Workflow questions** (specs, DBOS, task state, run status) → `workflow-copilot`

If a question spans multiple modules, the primary pilot synthesizes answers from delegated responses.

## Cached Documentation

Each agent has access to cached `README.md` and `AGENTS.md` files for its module:

- **Primary pilot**: `src/mash/core/README.md`, `src/mash/tools/README.md`, `src/mash/skills/README.md`, `src/mash/logging/README.md`, `src/mash/memory/README.md`, `src/mash/agents/masher/README.md`, plus top-level `README.md` and `src/mash/AGENTS.md`
- **Each copilot**: module-specific `README.md` and `AGENTS.md` files

Agents use cached docs as the primary source of truth before falling back to targeted `bash` verification.

## Host Composition

`pilot/spec.py` builds the Mash Pilot host with:

1. **Primary agent**: `pilot` — handles shared/cross-cutting questions
2. **Five copilots**: `cli-copilot`, `api-copilot`, `mcp-copilot`, `runtime-copilot`, `workflow-copilot`
3. **Masher workflows**: `masher-trace-digest` and `masher-online-eval-curation` (workflow-only, not subagents)
4. **Tools**:
   - `BashTool` — repository and terminal inspection
   - `UpdateDocsTool` — demonstrates `requires_approval` for gating documentation updates
   - `AskUserTool` — lets agents ask questions and durably wait for responses
5. **Skills**: Changelog skill (dynamically published on first use)

## Getting Started

### Prerequisites

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- PostgreSQL >= 14
- An Anthropic API key

### Install

```bash
cd mash-pilot
uv venv
uv pip install -e .
```

### Start PostgreSQL

```bash
# If you don't have Postgres running already
docker run -d --name mash-pg \
  -e POSTGRES_DB=mash-pilot \
  -e POSTGRES_USER=mash \
  -e POSTGRES_PASSWORD=mash \
  -p 5433:5432 \
  postgres:17-alpine
```

### Start the Pilot Host

```bash
export MASH_DATABASE_URL="postgresql://mash:mash@localhost:5433/mash-pilot
export ANTHROPIC_API_KEY=sk-ant-...
export PILOT_WORKSPACE_ROOT=/path/to/mashpy

mash host serve --host-app pilot.spec:build_host --port 8000
```

`PILOT_WORKSPACE_ROOT` must point at a local clone of the
[mashpy](https://github.com/imsid/mashpy) repository. The Pilot agents
operate on this source tree — reading READMEs, running bash commands, and
inspecting git history.

### Connect the Pilot REPL

In another terminal (with the same venv activated):

```bash
pilot repl
```

This opens an interactive REPL with Pilot-only slash commands. The CLI
defaults to `http://127.0.0.1:8000`.

### Example Questions

Inside the REPL:

```text
> Summarize how HostBuilder wires the primary agent, subagents, and workflows. Cite the key files.
> Trace how an accepted request moves through AgentRuntime, RuntimeStore, and RequestEngine.
> Explain when request.waiting is emitted and what that means for a busy session.
> Compare src/mash/runtime and src/mash/workflows responsibilities in this repo.
```

The primary pilot will delegate to the appropriate copilot and synthesize the answer.

## Pilot REPL Commands

### Standard Mash REPL Commands
- `/help` — show available commands
- `/status` — show agent and session status
- `/history [N]` — show last N turns
- `/clear` — clear session history

### Pilot-Only Commands
- `/changelog [N]` — show the last N commits with analysis (default: 5)

On first use, `/changelog` dynamically publishes a changelog skill and workflow against the primary `pilot` agent, then runs it with `commit_count=N`. Subsequent calls reuse the published skill.

## Tool Approval Demo

The primary pilot agent registers an `UpdateDocsTool` (defined in `pilot/tools.py`) with `requires_approval = True`.

When the agent plans to update a README.md or AGENTS.md file:

1. The runtime detects the tool call targets a tool with `requires_approval = True`
2. The runtime automatically pauses execution and emits a `request.interaction.create` event
3. The user is asked to approve, deny, or skip the update
4. If approved, the tool executes normally
5. If denied or skipped, the tool call is skipped and the agent receives an error result

This demonstrates the `requires_approval` interface — a single attribute on any tool that gates execution behind durable user consent without any additional wiring.

```python
from mash.tools.base import ToolResult


class UpdateDocsTool(Tool):
    name = "update_docs"
    requires_approval = True  # Gates execution behind user consent
    description = "Update README.md or AGENTS.md files."
    parameters = {
        "file_path": {"type": "string", "description": "Path to README.md or AGENTS.md"},
        "content": {"type": "string", "description": "Updated file content"},
    }

    async def execute(self, args):
        # Only runs if user approves
        file_path = args["file_path"]
        content = args["content"]
        Path(file_path).write_text(content)
        return ToolResult.success(f"Updated {file_path}")
```

## AskUser Demo

The pilot also registers `AskUserTool` — a built-in tool that lets the agent ask the user questions mid-execution and durably wait for their response.

```python
from mash.tools.ask_user import AskUserTool

tools.register(AskUserTool())
```

### How It Works

Unlike normal tools, `AskUserTool` is **intercepted at the workflow level** before execution. This allows the runtime to:

1. Detect the tool call
2. Emit a `request.interaction.create` event
3. Durably block until the user responds
4. Return the user's answer as a normal tool result
5. Survive runtime restarts (the interaction state is persisted)

### Interaction Types

The interaction type is determined automatically based on the `options` parameter:

- **Choice interaction** (with options): User selects from a list
  ```python
  AskUser(question="Which environment should I deploy to?", options=["staging", "production"])
  ```

- **Info interaction** (no options): User provides free-form text
  ```python
  AskUser(question="What's the database connection string?")
  ```

The LLM calls it naturally, and the runtime intercepts the tool call, emits a `request.interaction.create` event, durably blocks, and returns the user's answer as a normal tool result.

### Timeout Behavior

AskUser interactions have a default timeout of **1 hour** (3600 seconds). If the user does not respond within this window:

- The interaction completes with `timed_out = true`
- The agent receives the timeout status in the tool result metadata
- Agents should check the `timed_out` flag and handle gracefully (use a default, retry, or fail with a clear message)

## Deploying to Render

The repo includes a [Render Blueprint](render.yaml) that provisions the Pilot
host and a managed Postgres instance.

### One-Click Deploy

1. Push this repo to GitHub.
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** →
   **Blueprint**.
3. Connect the `mash-pilot` repo and select the branch.
4. Render detects `render.yaml` and shows the services to create:
   - **pilot** — Web Service (Docker)
   - **pilot-db** — PostgreSQL (Starter plan)
5. Set the `ANTHROPIC_API_KEY` secret when prompted (marked `sync: false` so
   Render asks for it during setup).
6. Click **Apply**.

Render builds the Docker image, provisions Postgres, injects
`MASH_DATABASE_URL` automatically, and starts the host. The Dockerfile clones
the [mashpy](https://github.com/imsid/mashpy) repo into the container so the
Pilot agents have the source tree to operate on.

### Auto-Deploy

Every push to the `mash-pilot` repo triggers a redeploy. The Docker build
clones mashpy `main` at build time, so the agents get a fresh copy of the
mashpy source on each mash-pilot deploy.

To also redeploy when mashpy changes, add a [Render Deploy Hook](https://docs.render.com/deploy-hooks)
and trigger it from a GitHub Actions workflow in the mashpy repo.

### Connect to the Render Instance

```bash
pilot repl --api-base-url https://pilot.onrender.com
```

Or set the env var so you don't need the flag:

```bash
export PILOT_API_BASE_URL=https://pilot.onrender.com
pilot repl
```

### Health Check

Render uses `/api/v1/health` to verify the service is ready before routing
traffic.

## Telemetry UI

The API server also serves the telemetry UI at:

- Local: [http://127.0.0.1:8000/telemetry](http://127.0.0.1:8000/telemetry)
- Render: `https://pilot.onrender.com/telemetry`

This provides real-time visibility into agent execution, request traces, and event logs.
