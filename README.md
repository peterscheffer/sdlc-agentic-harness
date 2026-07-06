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

## Spec profiles: deterministic verification

Features are specified through pluggable **spec profiles** — each pairs a spec
format with a deterministic, exit-code-based verifier. The planning stage
classifies the solution (ui / api / service / integration / data / mixed) and
recommends profiles; the requirements Q&A confirms them with you (or adopts the
recommendation automatically in auto-accept mode). A feature can combine
multiple profiles, and **all selected verifiers must exit 0** for the testing
gate to pass. LLM judgment is used only where determinism is impossible
(PRINCIPLES compliance, review recommendation).

| Profile | Spec artifact | Verifier (Python / Java / JS·TS) |
|---------|---------------|----------------------------------|
| `gherkin-bdd` | `sdlc/requirements/*.feature` | behave / cucumber-jvm (`mvn test`, `gradle test`) / @cucumber/cucumber |
| `unit-tests` | `sdlc/requirements/TEST_CASES.md` | pytest / JUnit / jest or vitest |
| `openapi-contract` | `sdlc/requirements/openapi.yaml` | schemathesis against the running service |
| `stitch-ui` | `sdlc/ui-design/DESIGN.md` + Stitch screen exports (`sdlc/ui-design/stitch/**/code.html`) | `design_tokens.py check` — every design token in the exports must be declared in the app's global stylesheet |

The coding stage generates step definitions and test skeletons as first-class
targets and runs each verifier inside its iteration loop, so runner failures
feed back into the next iteration. Runners are auto-detected from the project
(`pyproject.toml`, `pom.xml`, `build.gradle`, `package.json`, `tsconfig.json`)
and overridable per profile in `sdlc.config.json`:

```json
"default_profiles": ["gherkin-bdd"],
"profiles": {
  "gherkin-bdd": { "runner": "behave" },
  "unit-tests": { "tests_dir": "tests" },
  "openapi-contract": {
    "server_command": "uvicorn app:app --port 8000",
    "base_url": "http://127.0.0.1:8000",
    "health_path": "/health"
  },
  "stitch-ui": {
    "stitch_dir": "sdlc/ui-design/stitch",
    "css_path": "src/app/globals.css"
  }
}
```

The `stitch-ui` profile's spec artifacts are produced by the ui-design stage,
not the requirements stage: the ui-design skill retrieves generated screens
through the Stitch MCP connection (project → design system from DESIGN.md →
screens → `code.html` exports), or you export them manually from Stitch. The
requirements gate blocks until the exports exist; the coding loop
deterministically ports the embedded design tokens into the global stylesheet
(`design_tokens.py port`) before verifying; the testing stage re-checks the
final stylesheet so a dropped token fails the gate.

> **Breaking change:** the `gherkin-bdd` profile now requires a real BDD runner
> (it previously used an LLM compliance check). If the runner is not installed,
> the coding stage fails fast at preflight with the exact install command —
> there is no silent LLM fallback.

## Dark factory mode

`--auto-accept` runs the entire pipeline unattended: the skills skip
interactive Q&A (answering with best-practice defaults), planning auto-adopts
the recommended spec profiles, and every gate is verified deterministically
from planning through PR submission:

```bash
python3 .scripts/sdlc_harness.py --stage planning --feature "add a /health endpoint" --auto-accept
```

Interactive mode is unchanged — run the slash commands stage by stage and give
feedback at each Q&A gate.

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

Alternatively, you can run a single stage via the CLI:

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
| `--auto-accept` | Dark-factory mode: implies `--autopilot`; skills skip interactive Q&A and profile recommendations are auto-adopted |
| `--profiles <list>` | Comma-separated spec profiles override (`gherkin-bdd`, `unit-tests`, `openapi-contract`, `stitch-ui`) |
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
