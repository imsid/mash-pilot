# Pilot

A command-line guide to the [Mash](https://github.com/imsid/mashpy) codebase.

Instead of reading the docs, grepping the source, or asking a general-purpose
coding agent about Mash, you ask Pilot. It's built on Mash, and its agents
specialize in Mash's own modules — so it answers from the actual source tree,
not from a stale training snapshot.

```text
> Summarize how HostBuilder registers pooled agents and host compositions.
> Trace how an accepted request moves through AgentRuntime, RuntimeStore, and RequestEngine.
> When is request.waiting emitted, and what does it mean for a busy session?
> Compare src/mash/runtime and src/mash/workflows responsibilities.
```

## How it works

The `pilot` CLI talks to a Mash host running a team of copilots, each owning a
module of the Mash source. You ask a question; the primary guide routes it to
the copilot that owns the relevant module and synthesizes one answer. The
routing is visible live as subagent trace frames.

## Quick Start

```bash
# 1. Start the host — one container, embedded Postgres and the Mash source included
docker run -d --name pilot -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  `# or instead: -e OPENAI_API_KEY=sk-... (Anthropic wins if both are set)` \
  -v pilot-data:/var/lib/pilot \
  ghcr.io/imsid/mash-pilot:latest

# 2. Install the CLI and ask
curl -fsSL https://raw.githubusercontent.com/imsid/mash-pilot/main/install.sh | sh
pilot repl --host guide
```

Add `-e GITHUB_MCP_PAT=ghp_...` to enable the guide's commit-inspection tools
for the Mash repo. The `pilot-data` volume keeps the database and your
configuration durable across container restarts and upgrades.

The CLI defaults to `http://127.0.0.1:8000`; point it at a host running
elsewhere with `--api-base-url` or `PILOT_API_BASE_URL`. To bring your own
Postgres instead of the embedded one, set `MASH_DATABASE_URL` on the
container.

## The guide team

The `guide` host is the `pilot` primary plus six module copilots, each scoped
to one part of the Mash source:

| Agent | Owns |
|-------|------|
| `pilot` | Shared/cross-cutting: `core`, `tools`, `skills`, `logging`, `memory` |
| `cli-copilot` | `src/mash/cli` — commands, REPL, terminal rendering |
| `api-copilot` | `src/mash/api` — HTTP routes, FastAPI |
| `admin-copilot` | `src/mash/api/web-admin` — the admin dashboard SPA: tabs, components |
| `mcp-copilot` | `src/mash/mcp` — MCP client/server, transport, tool adaptation |
| `runtime-copilot` | `src/mash/runtime` — request lifecycle, event sourcing, durability |
| `workflow-copilot` | `src/mash/workflows` — DBOS orchestration, task state, run status |

`pilot browse` lists the full team and their scopes.

## Building with Mash

The guide also carries a `build-mash-agent` skill, so it goes beyond
explaining Mash to scaffolding your own Mash application:

```text
> Build me a customer support agent with a knowledge base search tool and human approval for refunds.
> Scaffold a multi-agent code reviewer with separate agents for security, style, and correctness.
> I need an agent that connects to my MCP server at localhost:3000 and uses Gemini as the LLM.
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `pilot repl --host guide` | Enter the guide and start asking (`--agent <id>` to talk to one copilot directly) |
| `pilot browse` | List the agents and their scopes |
| `pilot compose <host-id> --primary <agent> [--subagents a,b]` | Build a custom team — e.g. just the runtime + workflow copilots |
| `pilot hosts` | List the teams in your config file (`~/.pilot/hosts.json`) |
| `pilot serve` | Run your own host from a source install |

`pilot compose` writes to `~/.pilot/hosts.json` (plain JSON you can also edit);
the CLI publishes it to the host when you enter a REPL. The stock mash CLI
drives the same host too: `mash connect` / `mash compose` / `mash repl`.

## REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/agent` | List the agents in the current team |
| `/status` | Deployment status |
| `/history [N]` | View conversation history |
| `/trace [N]` | Span analysis for the last N traces |
| `/feedback <message>` | Record a note or bug report against the session |
| `/clear` | Clear the screen |
| `/changelog [N]` | Generate a changelog from the last N commits (sessions on the `pilot` primary) |
| `/quiz` | Interactive quiz about Mash internals (teams with the `pilot-quiz` workflow) |

## Admin Dashboard

The host serves an admin dashboard for visibility into the agents, sessions,
and logs at [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin) (or
`/admin` on whatever host you deployed).

> Looking for personal agents (a GitHub brief, a finance watcher)? Those moved
> to [mash-pa](https://github.com/imsid/mash-pa), with its own `pa` CLI. Pilot
> focuses on all things Mash.

## Development & Deployment

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development, Docker Compose
deployment, adding an agent to the catalog, and releasing CLI binaries.
</content>
