# Contributing to Pilot

This guide covers local development, running the host with Docker Compose,
publishing an agent to the catalog, and releasing standalone CLI binaries.

## Local Development

This is the loop for working on the catalog, the CLI, or the specs: run the
host from source so code changes don't need an image rebuild.

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python and the venv from
  `uv.lock`)
- Docker (for Postgres)
- An Anthropic API key
- A local clone of [mashpy](https://github.com/imsid/mashpy) — the source
  tree the Pilot agents operate on

### Setup

```bash
cd mash-pilot
uv sync                              # create the venv from uv.lock
docker compose up -d db              # Postgres only, published on 127.0.0.1:5433
cp .env.example .env
```

In `.env`, set `ANTHROPIC_API_KEY` and uncomment the local-development
block:

```
MASH_DATABASE_URL=postgresql://mash:mash@127.0.0.1:5433/mash_pilot
PILOT_WORKSPACE_ROOT=/path/to/mashpy
```

The database is `mash_pilot` with an underscore — everything else in this
project is `mash-pilot` with a hyphen, so this is an easy one to typo
(Postgres will report `database "mash-pilot" does not exist`).

`GITHUB_MCP_PAT` is optional: a GitHub personal access token (generate one
at **Settings → Developer settings → Personal access tokens**, `repo`
scope) that powers the `pilot` guide's commit-inspection tools. Without it
the guide still registers; it simply runs without the GitHub MCP tools.

Do not quote values in `.env` — `python-dotenv` treats quotes as literal
characters.

### Run

```bash
mash host serve --host-app pilot.spec:build_pool --port 8001
``` 
Then, in another terminal:

```bash
pilot browse                  # the pool + configured hosts
pilot repl --host guide       # enter the default composition
```

The CLI defaults to `http://127.0.0.1:8001`.

## The Docker Image

The published image (`ghcr.io/imsid/mash-pilot`) is dual-mode, selected by
`MASH_DATABASE_URL` in `docker-entrypoint.sh`:

- **unset** — single-container mode: the entrypoint initializes and starts
  an embedded Postgres on the data volume (`$PILOT_DATA_DIR/pg`), then runs
  the host. This is the README quick start.
- **set** — external-database mode: the embedded Postgres is skipped
  entirely and the host connects to yours. Use this when you want the
  database managed separately or scaled independently.

`docker compose up -d` runs the external-database mode locally: one Postgres
container plus the Pilot host built from source (`cp .env.example .env`
first). This is the standard dev loop for working on the image or catalog.

The Docker build clones the [mashpy](https://github.com/imsid/mashpy) repo
into the image so the Pilot agents have the source tree to operate on;
rebuild with `docker compose build --no-cache pilot` to pick up new mashpy
commits.

`GET /api/v1/health` reports readiness, useful as a probe if you put the
container behind a reverse proxy or orchestrator.

## Publishing an Agent to the Catalog

Adding an agent to the store is adding a package under
`pilot/catalog/agents/` and one entry to the `CATALOG` tuple.

1. **Create the package.** A directory under `pilot/catalog/agents/<name>/`
   with a `spec.py` implementation and an `__init__.py` that re-exports the
   agent id plus two callables:

   ```python
   def create_spec(*, workspace_root: str) -> AgentSpec: ...
   def build_metadata() -> AgentMetadata: ...
   ```

   The spec is a standard Mash `AgentSpec` (tools, LLM, system prompt,
   config). The `cli` copilot is the smallest complete example; the `pilot`
   primary shows the MCP pattern (`build_mcp_servers`) and subagent
   delegation.

2. **Write the listing carefully.** The `AgentMetadata` is both the store
   listing `pilot browse` renders and the delegation directory a primary
   reads when your agent serves as a subagent. Vague `usage_guidance`
   produces vague routing.

3. **Register it.** Add one `CatalogEntry` to `CATALOG` in
   `pilot/catalog/__init__.py`.

4. **Degrade gracefully.** If the agent needs credentials, register it
   unconditionally and gate the capability: return `[]` from
   `build_mcp_servers()` when unconfigured and let the system prompt explain
   what to set (see the `pilot` primary). The catalog should always be fully
   browsable.

5. **Ship data files as package data.** Add globs to
   `[tool.setuptools.package-data]` in `pyproject.toml` (see the
   `pilot/skills` entries) so the Docker `pip install .` includes them.

Rebuild the deployment (`docker compose build pilot && docker compose up -d`)
and the new listing appears in `pilot browse`, ready to be composed into
hosts. Workflow definitions (like `pilot-quiz`) are registered post-build in
`pilot/spec.py`; host configs attach them by id and the REPL enables the
matching command (`/quiz`) only in hosts that do.

## Releasing CLI Binaries

Tag a version to build and publish standalone CLI binaries:

```bash
git tag v0.2.0
git push origin v0.2.0
```

GitHub Actions builds `pilot` binaries for macOS (arm64) and Linux (x86_64)
via PyInstaller and uploads them to a GitHub Release. The same tag also
triggers the Docker workflow, which publishes the multi-arch
(amd64 + arm64) image to `ghcr.io/imsid/mash-pilot` tagged `latest` and the
version. One-time setup: after the first push, set the GHCR package to
public in the repo's package settings so `docker run` works without
authentication.

### Re-tagging a Release

If you need to rebuild a release (e.g., after fixing the build config), commit
your changes and push to `main` first, then delete the old tag/release and
re-tag at the new commit:

```bash
git add -A && git commit -m "fix release build"
git push origin main
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0
gh release delete v0.1.0 --yes
git tag v0.1.0
git push origin v0.1.0
```

The install script (`install.sh`) always fetches the latest release:

```bash
curl -fsSL https://raw.githubusercontent.com/imsid/mash-pilot/main/install.sh | sh
```

## Architecture

Pilot is a standard Mash application:

- `pilot/catalog/` — The agent catalog: each package is one store listing
  (`agents/` holds the `pilot` primary and its copilots; `workflows/` holds
  workflow-only agents), registered through the explicit `CATALOG` tuple in
  `catalog/__init__.py`
- `pilot/spec.py` — `build_pool()`: registers the catalog as a flat pool
  (no built-in hosts)
- `pilot/cli.py` — Standalone CLI, defaulting to `http://127.0.0.1:8000`
- `pilot/store.py` — The host config file (`~/.pilot/hosts.json`): the
  source of truth for compositions, seeded with `guide`, published to
  the deployment on REPL entry
- `pilot/tools.py` — Custom tools (`UpdateDocsTool` with `requires_approval`)
- `pilot/prompt.py` — System prompt construction
- `pilot/skills/` — Skill markdown files

The deployment is a flat pool of seven agents — the `pilot` guide family (a
primary plus five module copilots) and the `quiz-me` workflow agent — with
no built-in host compositions. Hosts are configuration: the CLI's config
file holds them (seeded with the `guide` composition), and entering a REPL
publishes them over the host
control API (`PUT /v1/hosts/{id}`, idempotent). Requests routed through a
host (`POST /v1/hosts/{id}/request`) give the primary an `InvokeSubagent`
tool and a directory of that host's subagents; bare requests to any agent
run it alone. Subagent delegation, tool approval, and durable interactions
are handled by the Mash runtime. The stock mash CLI can drive the same
deployment with `mash connect` / `mash compose` / `mash repl`. See the
[mashpy docs](https://github.com/imsid/mashpy) for framework details.
