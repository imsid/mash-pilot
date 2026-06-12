# Pilot

A multi-agent codebase guide for the [mashpy](https://github.com/imsid/mashpy)
project, built with the [Mash](https://github.com/imsid/mashpy) SDK.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/imsid/mash-pilot/main/install.sh | sh
pilot repl
```

## What Can Pilot Do?

### Explore the Mash Codebase

Ask Pilot anything about the Mash codebase. It delegates to specialized
copilots under the hood and synthesizes the answer.

```text
> Summarize how HostBuilder registers pooled agents and host compositions.
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

### Generate Changelogs

Pilot can generate changelogs from recent mashpy commits using the `/changelog`
REPL command. This is powered by Mash's **dynamic skills and workflows** —
the skill and workflow are registered on the fly when the command runs, showing
how Mash agents can extend their own capabilities at runtime.

```text
> /changelog        # last 5 commits
> /changelog 20     # last 20 commits
```

### Quiz Me

Test your understanding of Mash with the `/quiz` REPL command. Pilot generates
3 questions of increasing complexity about Mash internals and quizzes you
interactively. Ask follow-up questions at any point — the goal is learning,
not scoring. This is powered by a dedicated **workflow agent** registered at
startup, demonstrating how Mash runs workflow-only agents alongside the
pooled agents.

```text
> /quiz
```

## Agents

The deployment is a flat pool of six agents plus a code-defined `pilot` host
composition (primary `pilot`, the five copilots as subagents):

| Agent | Scope |
|-------|-------|
| `pilot` | Shared/cross-cutting: `core`, `tools`, `skills`, `logging`, `memory` |
| `cli-copilot` | `src/mash/cli` — commands, REPL, terminal rendering |
| `api-copilot` | `src/mash/api` — HTTP routes, FastAPI, telemetry UI |
| `mcp-copilot` | `src/mash/mcp` — MCP client/server, transport, tool adaptation |
| `runtime-copilot` | `src/mash/runtime` — request lifecycle, event sourcing, durability |
| `workflow-copilot` | `src/mash/workflows` — DBOS orchestration, task state, run status |

`pilot repl` routes messages through the `pilot` host, so the primary
delegates automatically based on the question. If a question spans modules,
it synthesizes answers from multiple copilots. Use `pilot repl --agent <id>`
to talk to one pooled agent directly with no delegation, or drive the same
deployment with the stock mash CLI: `mash connect` / `mash compose` /
`mash repl`.

## REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Agent and session status |
| `/history [N]` | Show last N turns |
| `/trace [N]` | Show span analysis for the last N traces |
| `/clear` | Clear session history |
| `/changelog [N]` | Generate changelog from last N commits (default: 5) |
| `/quiz` | Interactive quiz about Mash internals |

## Telemetry

The host serves a telemetry UI for real-time visibility into agent execution:

- Local: [http://127.0.0.1:8000/telemetry](http://127.0.0.1:8000/telemetry)
- Render: `https://pilot-tk3b.onrender.com/telemetry`

## Development & Deployment

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup, Render
deployment, and releasing CLI binaries.
