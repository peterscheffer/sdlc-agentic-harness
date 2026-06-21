# SDLC Agentic Harness

A stage-gated SDLC orchestration engine that forces every code change
through a structured, gate-verified pipeline — from intent parsing through
architecture, code generation, testing, self-review, and GitHub PR submission —
with no stage advancing until its hard completion criteria are satisfied.

It's built for AI engineers who want specification-specific results, verified outcomes with their own definition of verification, LLM routing based on cost & capability, configurable stages and models.  Specifically, this harness is designed to enforce your coding practices, and your architecture practices.  It does this by making your verification handler plug and play - you write the StageGate GateCheck, and the harness will run it, and unless it passes, the stage isn't complete.  This leaves you to be hands-off and worry free while doing loop coding.

## Capabilities
Read about this harness's capablities in the [Documentation](https://peterscheffer.github.io/sdlc-agentic-harness/index.html)

[SDLC Stages](https://peterscheffer.github.io/sdlc-agentic-harness/stages.html)  
[Gate-based Verification](https://peterscheffer.github.io/sdlc-agentic-harness/gates.html)  
[Dual Verification Methods](https://peterscheffer.github.io/sdlc-agentic-harness/verification.html)  
[Iterative Coding Loop](https://peterscheffer.github.io/sdlc-agentic-harness/coding-loop.html)  
[LLM Interaction Logging](https://peterscheffer.github.io/sdlc-agentic-harness/logging.html)  
[State Persistence & Crash Recovery](https://peterscheffer.github.io/sdlc-agentic-harness/state.html)  
[Architecture Principles Enforcement](https://peterscheffer.github.io/sdlc-agentic-harness/principles.html)  
[Gherkin Specifications](https://peterscheffer.github.io/sdlc-agentic-harness/gherkin.html)  
[Structured Self-Review & PR Submission](https://peterscheffer.github.io/sdlc-agentic-harness/review-pr.html)  
[CLI Command Reference](https://peterscheffer.github.io/sdlc-agentic-harness/cli.html)  
[Stage & LLM Provider Configuration](https://peterscheffer.github.io/sdlc-agentic-harness/config.html)

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

## Installation

This repo provides a collection of useful `.claude/commands` (custom slash commands) and related files for **Claude Code** (and compatible tools like **OpenCode**).

### Recommended: Add to your existing project

Clone the necessary files into your project's root directory:

```bash
git clone --depth 1 https://github.com/peterscheffer/sdlc-agentic-harness.git /tmp/sdlc-harness
cp -r /tmp/sdlc-harness/.claude .
cp -r /tmp/sdlc-harness/.opencode .
cp -r /tmp/sdlc-harness/.scripts .
cp -r /tmp/sdlc-harness/.env.example .
cp -r /tmp/sdlc-harness/.gitignore .
cp -r /tmp/sdlc-harness/sdlc.config.json .
rm -rf /tmp/sdlc-harness
```

Then start Claude Code or OpenCode from your project folder:

```bash
claude
```

```bash
opencode
```

## Usage

Use slash commands inside Claude or Opencode, starting with:

```bash
/plan
```

Alternatively, you can run a single stagevia the CLI:

```bash
python3 .scripts/sdlc_harness.py --stage planning --feature "Add CSV export to the reports page"
```

You can auto-run all remaining stages after architecture:

```bash
python3 .scripts/sdlc_harness.py --stage coding --feature "..." --autopilot
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


### Claude slash commands

If you use [Claude](https://claude.ai), the [`.claude/commands/`](.claude/commands)
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
  sdlc_harness.py       # CLI entry point + orchestration
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
- [docs/PRINCIPLES.md](docs/PRINCIPLES.md) — PRINCIPLES template for engineering practices rule enforcement
- [sdlc/templates/PRD.md](sdlc/templates/PRD.md) — Product Requirements Document template 
- [capabilities](https://peterscheffer.github.io/sdlc-agentic-harness/) — capability reference (HTML)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). For security reports, see
[SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Peter Scheffer
