# Pilot

A multi-agent codebase guide for the [mashpy](https://github.com/imsid/mashpy)
project, built with the [Mash](https://github.com/imsid/mashpy) SDK.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/imsid/mash-pilot/main/install.sh | sh
pilot repl --api-base-url https://pilot.onrender.com
```

Or set the URL once:

```bash
export PILOT_API_BASE_URL=https://pilot.onrender.com
pilot repl
```

## What Can Pilot Do?

### Explore the Mash Codebase

Ask Pilot anything about the Mash codebase. It delegates to specialized
copilots under the hood and synthesizes the answer.

```text
> Summarize how HostBuilder wires the primary agent, subagents, and workflows.
> Trace how an accepted request moves through AgentRuntime, RuntimeStore, and RequestEngine.
> Explain when request.waiting is emitted and what that means for a busy session.
> Compare src/mash/runtime and src/mash/workflows responsibilities.
```

### Build Mash Agents

Pilot includes a `build-mash-agent` skill that can scaffold and guide you
through building your own Mash-powered agent applications. Ask it to generate
agent code from a description.

```text
> Build me a customer support agent with a knowledge base search tool and human approval for refunds.
> Scaffold a multi-agent code reviewer with separate agents for security, style, and correctness.
> Create a data pipeline orchestrator that runs three analysis steps in sequence using workflows.
> I need an agent that connects to my MCP server at localhost:3000 and uses Gemini as the LLM.
```

## Agents

| Agent | Scope |
|-------|-------|
| `pilot` (primary) | Shared/cross-cutting: `core`, `tools`, `skills`, `logging`, `memory` |
| `cli-copilot` | `src/mash/cli` — commands, REPL, terminal rendering |
| `api-copilot` | `src/mash/api` — HTTP routes, FastAPI, telemetry UI |
| `mcp-copilot` | `src/mash/mcp` — MCP client/server, transport, tool adaptation |
| `runtime-copilot` | `src/mash/runtime` — request lifecycle, event sourcing, durability |
| `workflow-copilot` | `src/mash/workflows` — DBOS orchestration, task state, run status |

The primary agent delegates automatically based on the question. If a question
spans modules, it synthesizes answers from multiple copilots.

## REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Agent and session status |
| `/history [N]` | Show last N turns |
| `/clear` | Clear session history |
| `/changelog [N]` | Generate changelog from last N commits (default: 5) |

## Telemetry

The host serves a telemetry UI for real-time visibility into agent execution:

- Local: [http://127.0.0.1:8000/telemetry](http://127.0.0.1:8000/telemetry)
- Render: `https://pilot.onrender.com/telemetry`

## Development & Deployment

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup, Render
deployment, and releasing CLI binaries.
