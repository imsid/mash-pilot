# Pilot

Your self-hosted app store for agents, built with the
[Mash](https://github.com/imsid/mashpy) SDK.

The [Mash product brief](https://github.com/imsid/mashpy/blob/main/docs/posts/product-brief.md)
argues that agents will proliferate the way apps did once the app store gave
them a standard place to live, and that the **Host** is the seam a user
application integrates with. Pilot is the reference user application on that
seam — it plays the app store:

| App store concept | Mash concept | In Pilot |
|---|---|---|
| The catalog | The agent pool | `pilot/catalog/`, registered by `build_pool()` |
| An app listing | `AgentMetadata` | `pilot browse` |
| Installing an app | `PUT /v1/hosts/{id}` | `pilot compose` |
| An installed app | A `Host` composition | An entry in `~/.pilot/hosts.json`, published on connect |
| Launching an app | `POST /v1/hosts/{id}/request` | `pilot repl --host <id>` |

The deployment is yours: run the store on your laptop or your own server.
Agents ship in the catalog; you compose them into teams; your applications —
here, a terminal CLI — talk to compositions over plain HTTP + SSE.

## Quick Start

```bash
# 1. Start your store — one container, embedded Postgres included
docker run -d --name pilot -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v pilot-data:/var/lib/pilot \
  ghcr.io/imsid/mash-pilot:latest

# 2. Install the CLI and walk in
curl -fsSL https://raw.githubusercontent.com/imsid/mash-pilot/main/install.sh | sh
pilot browse                # see what the store ships
pilot repl --host mash-guide   # enter the default composition
```

Add `-e GITHUB_MCP_PAT=ghp_...` to light up the morning-brief agent. The
`pilot-data` volume keeps the database, your ledger, and everything else
durable across container restarts and upgrades.

The CLI defaults to `http://127.0.0.1:8000`; point it at a store running
elsewhere with `--api-base-url` or `PILOT_API_BASE_URL`. To bring your own
Postgres instead of the embedded one, set `MASH_DATABASE_URL` on the
container — that's all the [docker compose setup](CONTRIBUTING.md) does.

## Composing Teams

The pool is flat — which agents work together is your configuration, not
the deployment's. `pilot browse` shows the pool and your configured hosts;
`pilot compose` creates or replaces one; `pilot repl --host` enters it:

```bash
pilot compose my-morning --primary morning-brief --subagents finance-watch
pilot repl --host my-morning
```

Compositions live in the **host config file** (`~/.pilot/hosts.json`) — the
source of truth `pilot hosts` lists. It ships with the `mash-guide`
composition as its default entry, and it's plain JSON you can edit. Hosts on
the deployment are just published copies: a host is a few strings the server
validates and holds in memory, and the CLI re-publishes your config
(idempotent PUTs) every time it enters a REPL, so deployment restarts don't
matter.

Inside `pilot repl --host <id>` everything is scoped to that host: plain
messages route to its primary, delegation is limited to its subagents, and
`/agents` lists exactly the team you composed. To change the team, exit,
re-run `pilot compose` (define-or-replace), and re-enter — or switch with
`pilot repl --host <other>`.

## The Catalog

Nine pooled agents ship in `pilot/catalog/`, each with the listing metadata
that powers both the storefront and delegation routing:

**Personal agents**

| Agent | Listing |
|-------|---------|
| `morning-brief` | Your GitHub world — reviews requested, open PRs, assigned issues — via the GitHub MCP server with a read-only tool allowlist |
| `finance-watch` | A local transactions ledger — odd charges, duplicates, subscription drift. No credentials, no network; data never leaves the deployment |

**The Mash Guide family** — a multi-agent guide to the Mash codebase. Its
composition (primary + five module copilots as subagents) ships as the
default entry in your host config file:

| Agent | Scope |
|-------|-------|
| `mash-guide` | Shared/cross-cutting: `core`, `tools`, `skills`, `logging`, `memory` |
| `cli-copilot` | `src/mash/cli` — commands, REPL, terminal rendering |
| `api-copilot` | `src/mash/api` — HTTP routes, FastAPI, telemetry UI |
| `mcp-copilot` | `src/mash/mcp` — MCP client/server, transport, tool adaptation |
| `runtime-copilot` | `src/mash/runtime` — request lifecycle, event sourcing, durability |
| `workflow-copilot` | `src/mash/workflows` — DBOS orchestration, task state, run status |

The ninth agent is `quiz-me`, which executes the `pilot-quiz` workflow.
Workflows are attached to hosts in your config
(`"workflows": ["pilot-quiz"]` on `mash-guide` by default, or
`pilot compose ... --workflows pilot-quiz`), and the `/quiz` command exists
only in REPLs of hosts that attach it. One workflow-only agent (Mash's
built-in Masher) also runs beside the pool, hidden from listings and
compositions.

## The Featured App: Mash Guide

`pilot repl --host mash-guide` opens the codebase guide. The primary
delegates to the copilot that owns the relevant module and synthesizes the
answer; the routing is visible live as subagent trace frames.

```text
> Summarize how HostBuilder registers pooled agents and host compositions.
> Trace how an accepted request moves through AgentRuntime, RuntimeStore, and RequestEngine.
> Explain when request.waiting is emitted and what that means for a busy session.
> Compare src/mash/runtime and src/mash/workflows responsibilities.
```

It also carries a `build-mash-agent` skill, so it can go from answering
questions about Mash to scaffolding your own Mash application:

```text
> Build me a customer support agent with a knowledge base search tool and human approval for refunds.
> Scaffold a multi-agent code reviewer with separate agents for security, style, and correctness.
> I need an agent that connects to my MCP server at localhost:3000 and uses Gemini as the LLM.
```

## Personal Agents

The two personal agents bracket the integration space. **Morning Brief**
prepares a compact brief of your GitHub world — PRs awaiting your review,
your open PRs, assigned issues, recent repo activity — through the GitHub
MCP server with a read-only tool allowlist (set `GITHUB_MCP_PAT` in `.env`;
without it the agent stays in the catalog and explains how to configure
itself). **Finance Watch** watches a transactions ledger at
`$PILOT_DATA_DIR/transactions.csv` — flagging duplicate charges, new
merchants, subscription price changes, and outliers — with no credentials
and no network. A synthetic sample ledger is seeded on first start so it
works out of the box.

```text
pilot repl --agent morning-brief     # "what needs my review today?"
pilot repl --agent finance-watch     # "any odd charges this month?"
```

## Every Piece Demos a Mash Feature

Pilot is the reference application behind the
[Mash docs](https://github.com/imsid/mashpy), so each part of the store
exercises a framework feature end to end:

| What you see | Mash feature |
|---|---|
| `pilot compose` + re-publish on connect | Dynamic host composition; hosts as data |
| The approval pause on mash-guide's `update_docs` tool | Durable human-in-the-loop interactions |
| Copilot routing in `mash-guide` | `InvokeSubagent` + metadata as the delegation directory |
| `/changelog [N]` | Dynamic skills and workflows, registered at runtime |
| `/quiz` | Workflows attached to hosts, executed by a pooled agent |
| `/trace [N]` | Trace analysis: timing breakdowns, per-tool stats |
| `morning-brief` | Remote tools over MCP with a per-agent allowlist |

## CLI Commands

| Command | Description |
|---------|-------------|
| `pilot browse` | Browse the agent pool, the attachable workflows, and your configured hosts |
| `pilot compose <host-id> --primary <agent> [--subagents a,b] [--workflows w]` | Compose agents into a host (define-or-replace) |
| `pilot hosts` | List the hosts in your config file |
| `pilot repl --host <id>` | Enter a host's REPL, scoped to its team (`--agent <id>` for one bare agent) |
| `pilot serve` | Run your own Pilot host from a source install |

The stock mash CLI drives the same deployment: `mash connect` /
`mash compose` / `mash repl`.

## REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/agents` | List the agents composed in the current host |
| `/status` | Agent and session status |
| `/history [N]` | Show last N turns |
| `/trace [N]` | Show span analysis for the last N traces |
| `/clear` | Clear session history |
| `/changelog [N]` | Generate changelog from last N commits (sessions targeting `mash-guide`) |
| `/quiz` | Interactive quiz about Mash internals (hosts with the `pilot-quiz` workflow) |

## Telemetry

The host serves a telemetry UI for real-time visibility into agent execution
at [http://127.0.0.1:8000/telemetry](http://127.0.0.1:8000/telemetry) (or
`/telemetry` on whatever host you deployed).

## Development & Deployment

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development, Docker Compose
deployment, publishing an agent to the catalog, and releasing CLI binaries.
