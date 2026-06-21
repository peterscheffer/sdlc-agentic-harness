# SDLC Agentic Harness

A LangGraph-style SDLC orchestration engine that forces every code change
through a structured, gate-verified pipeline — from intent parsing through
architecture, code generation, testing, self-review, and GitHub PR submission —
with no stage advancing until its hard completion criteria are satisfied.

It's built for solo developers who want disciplined, repeatable, AI-assisted
development instead of ad-hoc prompting.

## The pipeline

```
planning → ui-design → architecture → requirements → coding → testing → review → pr
```

Each stage is driven by an LLM, validated by a gate, and persisted to state so a
run can be resumed or inspected at any point. Stages only advance when their
completion criteria pass.

## Requirements

- Python 3.11+
- An OpenAI-compatible LLM endpoint — local [Ollama](https://ollama.com),
  [OpenRouter](https://openrouter.ai), or OpenAI

## Install

```bash
git clone https://github.com/peterscheffer/sdlc-agentic-harness.git
cd sdlc-agentic-harness

pip install langchain-openai pydantic python-dotenv

cp .env.example .env   # then fill in your own values
```

Configure provider/model and your project's test/lint/build commands in
[`sdlc.config.json`](sdlc.config.json). Full setup notes are in
[docs/installation.md](docs/installation.md).

## Usage

Run a single stage:

```bash
python3 .scripts/langgraph_sdlc.py --stage planning --feature "Add CSV export to the reports page"
```

Run a stage and then auto-run all remaining stages:

```bash
python3 .scripts/langgraph_sdlc.py --stage planning --feature "..." --autopilot
```

Inspect or reset pipeline state:

```bash
python3 .scripts/langgraph_sdlc.py status
python3 .scripts/langgraph_sdlc.py reset [--force]
```

| Flag | Purpose |
|------|---------|
| `--stage <name>` | Target stage: `planning`, `ui-design`, `architecture`, `requirements`, `coding`, `testing`, `review`, `pr` |
| `--feature`, `--intent` | The intent / feature description (used by planning) |
| `--context <file>` | Path to a file containing prior conversation context |
| `--autopilot`, `-a` | After the requested stage succeeds, run all remaining stages |
| `--force` | Skip confirmation (reset) or force PR submission |

### OpenCode slash commands

If you use [OpenCode](https://opencode.ai), the [`.opencode/commands/`](.opencode/commands)
directory exposes the stages as slash commands (`/plan`, `/architect`,
`/coding`, `/requirements`, `/testing`, `/review`, `/pr`, `/ui-design`).

## Configuration

[`sdlc.config.json`](sdlc.config.json) controls per-stage models, the provider,
the shell commands the pipeline runs (`test`/`lint`/`build`), coverage
thresholds, the GitHub base branch, and timeouts. Secrets and observability
settings live in `.env` (see [`.env.example`](.env.example)).

LangSmith tracing is optional; when enabled, each LLM call is traced with
`stage`, `pipeline_id`, and `iteration` metadata.

## Repository layout

```
.scripts/
  langgraph_sdlc.py     # CLI entry point + orchestration
  nodes/                # per-stage logic (planning, architecture, coding, ...)
  gates/                # gate runner + PRINCIPLES enforcement
  utils/                # state, config, git, llm, validators
.opencode/commands/     # OpenCode slash-command definitions
tests/                  # pytest suite (Gherkin scenario coverage)
docs/                   # PRD, principles, capabilities reference
sdlc.config.json        # pipeline configuration
```

## Testing

```bash
python -m pytest tests/ -q
```

Tests run without real API calls via a mock LLM (`SDLC_USE_MOCK_LLM=1`).

## Documentation

- [docs/installation.md](docs/installation.md) — setup and configuration
- [docs/PRINCIPLES.md](docs/PRINCIPLES.md) — architecture rules the pipeline enforces
- [docs/capabilities/](docs/capabilities) — capability reference (HTML)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). For security reports, see
[SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Peter Scheffer
