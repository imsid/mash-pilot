# Contributing to Pilot

This guide covers local development, deploying to Render, and releasing
standalone CLI binaries.

## Local Development

### Prerequisites

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- PostgreSQL >= 14
- An Anthropic API key
- A local clone of [mashpy](https://github.com/imsid/mashpy)

### Install

```bash
cd mash-pilot
uv venv
uv pip install -e .
```

### Start PostgreSQL

```bash
docker run -d --name mash-pg \
  -e POSTGRES_DB=mash_pilot \
  -e POSTGRES_USER=mash \
  -e POSTGRES_PASSWORD=mash \
  -p 5433:5432 \
  postgres:17-alpine
```

### Configure Environment

Create a `.env` file in the repo root:

```
MASH_DATABASE_URL=postgresql://mash:mash@127.0.0.1:5433/mash_pilot
ANTHROPIC_API_KEY=sk-ant-...
PILOT_WORKSPACE_ROOT=/path/to/mashpy
GITHUB_MCP_PAT=ghp_...
```

`PILOT_WORKSPACE_ROOT` must point at a local clone of the mashpy repository.
The Pilot agents operate on this source tree — reading READMEs, running bash
commands, and inspecting git history.

`GITHUB_MCP_PAT` is a GitHub personal access token used to connect to the
GitHub MCP server. The pilot agent uses it to inspect commits and history on
the mashpy repository. Generate one at
**Settings → Developer settings → Personal access tokens** with `repo` scope.
If omitted, the MCP server is skipped and the agent loses access to GitHub
tools like `list_commits` and `get_commit`.

Do not quote values in `.env` — `python-dotenv` treats quotes as literal
characters.

### Start the Host

```bash
mash host serve --host-app pilot.spec:build_host --port 8000
```

### Connect the REPL

In another terminal (with the same venv activated):

```bash
pilot repl
```

The CLI defaults to `http://127.0.0.1:8000`.

## Deploying to Render

The repo includes a [Render Blueprint](render.yaml) that provisions the Pilot
host and a managed Postgres instance.

### Setup

1. Push this repo to GitHub.
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** →
   **Blueprint**.
3. Connect the `mash-pilot` repo and select the branch.
4. Render detects `render.yaml` and shows the services to create:
   - **pilot** — Web Service (Docker)
   - **pilot-db** — PostgreSQL
5. Set the `ANTHROPIC_API_KEY` secret when prompted.
6. Click **Apply**.

Render builds the Docker image, provisions Postgres, injects
`MASH_DATABASE_URL` automatically, and starts the host. The Dockerfile clones
the [mashpy](https://github.com/imsid/mashpy) repo into the container so the
Pilot agents have the source tree to operate on.

### Auto-Deploy

Every push to the `mash-pilot` repo triggers a redeploy. The Docker build
clones mashpy `main` at build time, so the agents get a fresh copy of the
mashpy source on each mash-pilot deploy.

To also redeploy when mashpy changes, add a
[Render Deploy Hook](https://docs.render.com/deploy-hooks) and trigger it from
a GitHub Actions workflow in the mashpy repo.

### Health Check

Render uses `/api/v1/health` to verify the service is ready before routing
traffic.

## Releasing CLI Binaries

Tag a version to build and publish standalone CLI binaries:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions builds `pilot` binaries for macOS (arm64 + x86_64) and Linux
(x86_64) via PyInstaller and uploads them to a GitHub Release.

The install script (`install.sh`) always fetches the latest release:

```bash
curl -fsSL https://raw.githubusercontent.com/imsid/mash-pilot/main/install.sh | sh
```

## Architecture

Pilot is a standard Mash application:

- `pilot/spec.py` — Agent specs and `build_host()` entry point
- `pilot/cli.py` — Standalone CLI with default Render URL
- `pilot/tools.py` — Custom tools (`UpdateDocsTool` with `requires_approval`)
- `pilot/prompt.py` — System prompt construction
- `pilot/changelog.py` — Dynamic changelog workflow
- `pilot/skills/` — Skill markdown files

The host runs one primary agent (`pilot`) and five subagents, all in-process.
Subagent delegation, tool approval, and durable interactions are handled by the
Mash runtime. See the [mashpy docs](https://github.com/imsid/mashpy) for
framework details.
