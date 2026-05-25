# Product Requirements Document
## [PROJECT_NAME] — LangGraph SDLC Orchestration Engine for OpenCode

| Field | Value |
|-------|-------|
| **Version** | 0.1.0-draft |
| **Status** | Draft |
| **Last Updated** | 2026-05-25 |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals](#3-goals)
4. [Non-Goals](#4-non-goals)
5. [User Persona](#5-user-persona)
6. [System Architecture Overview](#6-system-architecture-overview)
7. [SDLC Stage Definitions](#7-sdlc-stage-definitions)
8. [OpenCode Integration](#8-opencode-integration)
9. [Data Schemas](#9-data-schemas)
10. [Repository Structure](#10-repository-structure)
11. [Technical Stack](#11-technical-stack)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Error Handling](#13-error-handling)
14. [Open Questions](#14-open-questions)

---

## 1. Executive Summary

[PROJECT_NAME] is a local, developer-owned SDLC enforcement engine that wraps a LangGraph state machine behind OpenCode's slash command interface. It forces every code change through a structured, gate-verified pipeline — from intent parsing through architecture review, code generation, testing, self-review, and GitHub PR submission — with no stage advancing until its hard completion criteria are satisfied.

The system is designed for a solo developer who wants the discipline of an enterprise pipeline without the overhead of one. The entire pipeline is resumable across terminal sessions, produces auditable artefacts, and enforces project-specific architectural rules defined in a developer-authored `PRINCIPLES.md`.

---

## 2. Problem Statement

AI coding assistants are powerful but undisciplined. Left unconstrained, they:

- Skip design and planning phases, jumping straight to code generation
- Accumulate context rot across long sessions, degrading output quality
- Have no concept of "done" — they continue generating unless externally stopped
- Produce no auditable artefacts (no PRD, no architecture doc, no test evidence)
- Cannot enforce project-specific conventions or architectural guardrails

A developer who wants structured, reproducible, and reviewable AI-assisted outputs currently has no tool that enforces a complete SDLC with hard gate checks between stages.

---

## 3. Goals

| ID | Goal |
|----|------|
| G1 | Enforce a sequential, gate-verified SDLC pipeline via OpenCode slash commands |
| G2 | Persist full pipeline state to disk; survive terminal restarts and context wipes |
| G3 | Isolate each stage in its own LangGraph subgraph to prevent context rot |
| G4 | Support per-stage LLM model configuration |
| G5 | Provide a schema for a project-level `PRINCIPLES.md` guardrails document that the pipeline enforces |
| G6 | Perform a structured self-review and submit a GitHub Pull Request as the final pipeline output |
| G7 | Be installable as an open-source tool adoptable on any project |

---

## 4. Non-Goals

| ID | Non-Goal |
|----|----------|
| NG1 | Auto-merging branches |
| NG2 | Cloud deployment or infrastructure provisioning |
| NG3 | Ticket or issue management (Jira, Linear, GitHub Issues) |
| NG4 | Multi-user or team collaboration features |
| NG5 | A hosted SaaS version |
| NG6 | Support for git providers other than GitHub (v1 scope) |
| NG7 | Windows support (v1 scope) |

---

## 5. User Persona

**The Disciplined Solo Developer**

- Builds non-trivial software alone: side projects, internal tools, or open-source work
- Uses OpenCode as their primary AI coding assistant
- Wants AI-generated code to respect their own architectural rules consistently
- Is comfortable with the terminal and does not require a GUI
- Wants an auditable paper trail for every feature they ship

---

## 6. System Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│  OpenCode  (Terminal UI)                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  .opencode/commands/sdlc.md   (slash command definition) │  │
│  └───────────────────────────┬──────────────────────────────┘  │
└──────────────────────────────┼─────────────────────────────────┘
                               │  /sdlc <stage> "<intent>"
                               ▼
┌────────────────────────────────────────────────────────────────┐
│  LangGraph Pipeline  (scripts/sdlc_pipeline.py)                │
│                                                                │
│  ┌──────────┐  ┌───────────┐  ┌──────┐  ┌────────┐  ...      │
│  │ planning │→ │ ui-design │→ │ arch │→ │ coding │           │
│  │  (node)  │  │  (node)   │  │(node)│  │ (loop) │           │
│  └──────────┘  └───────────┘  └──────┘  └────────┘           │
│       │              │             │          │                │
│  Gate Check    Gate Check    Gate Check  Gate Check            │
└──────────────────────────────────┬─────────────────────────────┘
                                   │
                   ┌───────────────┼───────────────┐
                   ▼               ▼               ▼
            .sdlc_state.json   PRINCIPLES.md   GitHub PR
            (flat file state)  (guardrails)    (gh CLI)
```

The pipeline is a LangGraph directed graph. Each node represents one SDLC stage. A node executes, writes artefacts, runs hard gate checks, then halts. The subsequent stage starts only when the developer explicitly issues the next slash command.

Both OpenCode's LLM (acting as the display and relay layer) and the LangGraph nodes (acting as the reasoning layer) may invoke models. The LangGraph nodes are the authoritative source of generated artefacts; OpenCode's role is to execute the pipeline script and surface its output.

---

## 7. SDLC Stage Definitions

### 7.1 Stage Overview

| Order | Stage ID | Required | Output Artefact |
|-------|----------|----------|-----------------|
| 1 | `planning` | Yes | `sdlc/planning/PRD.md` |
| 2 | `ui-design` | No | `sdlc/ui-design/DESIGN.md` |
| 3 | `architecture` | Yes | `sdlc/architecture/ARCH.md` |
| 4 | `coding` | Yes | Modified source files |
| 5 | `testing` | Yes | `sdlc/testing/TEST_REPORT.md` |
| 6 | `review` | Yes | `sdlc/review/REVIEW.md` |
| 7 | `pr` | Yes | GitHub PR URL |

All artefact files are committed to the repository under `sdlc/`. The pipeline will not advance past a stage until all of that stage's gate checks pass.

---

### 7.2 Stage: `planning`

**Purpose:** Parse the developer's intent and produce a structured PRD.

**Inputs:**
- Developer intent string (passed as `/sdlc planning "<intent>"`)
- `PRINCIPLES.md` (read-only)
- Existing codebase (read-only scan for context)

**LangGraph node behaviour:**
- Calls the configured planning model to generate `sdlc/planning/PRD.md`
- PRD format is defined in §9.1
- Writes output, then halts awaiting developer review

**Gate checks (ALL must pass before `architecture` can start):**
- [ ] `sdlc/planning/PRD.md` exists
- [ ] PRD contains all required sections per §9.1 schema (validated by heading detection)
- [ ] PRD contains at least one task in the `## Tasks` section

**OpenCode output:**
```
[planning] ✓ PRD.md written to sdlc/planning/PRD.md
[planning] ✓ Gate checks passed (3/3)

Review sdlc/planning/PRD.md, then run: /sdlc ui-design  (or /sdlc architecture to skip UI)
```

---

### 7.3 Stage: `ui-design` (Optional)

**Purpose:** Generate a `DESIGN.md` UI specification for any interface changes described in the PRD.

**Inputs:**
- `sdlc/planning/PRD.md`
- `PRINCIPLES.md` (read-only)

**Activation logic:**
- The stage is automatically skipped if the PRD contains no UI-relevant keywords: `component`, `page`, `view`, `screen`, `UI`, `frontend`, `form`, `modal`, `layout`
- The developer can force-skip it by running `/sdlc architecture` directly
- The developer can force-run it with `/sdlc ui-design` regardless of PRD content

**LangGraph node behaviour:**
- Generates `sdlc/ui-design/DESIGN.md` conforming to the Google Stitch `DESIGN.md` specification
- Reference: https://stitch.withgoogle.com/docs/design-md/overview
- Halts and awaits developer review

**Gate checks:**
- [ ] `sdlc/ui-design/DESIGN.md` exists
- [ ] File contains the required Stitch top-level sections (per §9.2)

---

### 7.4 Stage: `architecture`

**Purpose:** Produce an architecture decision record and validate it against `PRINCIPLES.md`.

**Inputs:**
- `sdlc/planning/PRD.md`
- `sdlc/ui-design/DESIGN.md` (if present)
- `PRINCIPLES.md`
- Existing codebase (read-only scan)

**LangGraph node behaviour:**
- LLM generates `sdlc/architecture/ARCH.md` (schema in §9.3)
- A separate validator call checks `ARCH.md` against every rule in `PRINCIPLES.md`
- Violations are written into the `## PRINCIPLES Compliance` section of `ARCH.md`
- The node MUST fail if any rule with `severity: error` is violated
- Rules with `severity: warning` are reported but do not block progression

**Gate checks:**
- [ ] `sdlc/architecture/ARCH.md` exists
- [ ] `ARCH.md` contains all required sections per §9.3
- [ ] Zero `severity: error` PRINCIPLES violations reported

---

### 7.5 Stage: `coding`

**Purpose:** Iteratively generate and correct code changes until the build is clean.

**Inputs:**
- `sdlc/architecture/ARCH.md`
- `sdlc/planning/PRD.md`
- `PRINCIPLES.md`
- The specific target files listed in `ARCH.md`

**LangGraph node behaviour (the Ralph Loop):**

This stage is implemented as a LangGraph loop subgraph. The maximum iteration count is configurable in `sdlc.config.json` (default: `5`).

Each iteration:
1. The LLM receives only: `ARCH.md`, the current state of target files, and (from iteration 2 onwards) the specific gate failure reason from the previous iteration
2. The LLM generates or modifies the target source files
3. Gate checks execute
4. If all gate checks pass → loop exits; stage completes
5. If any gate check fails → iteration context is cleared entirely; the failure reason alone is carried into the next iteration

If maximum iterations are reached without all gate checks passing, the stage fails. A full iteration log is written to `sdlc/coding/ITERATIONS.md` and the developer is notified.

**Context isolation:** Each loop iteration MUST start with a fresh LLM call context. No prior conversation history is carried between iterations. This is the primary mechanism for preventing context rot.

**Gate checks:**
- [ ] Linter command (configured in `sdlc.config.json`) exits with code 0
- [ ] Build command (configured in `sdlc.config.json`) exits with code 0
- [ ] All files listed under `## Target Files` in `ARCH.md` exist on disk

---

### 7.6 Stage: `testing`

**Purpose:** Execute the project's test suite and validate coverage thresholds.

**Inputs:**
- Modified source files from the `coding` stage
- `sdlc.config.json` (test command, coverage settings)

**LangGraph node behaviour:**
- Executes the configured test command as a subprocess
- Captures stdout, stderr, and exit code
- Parses coverage output if `coverage.enabled: true` in config
- Writes `sdlc/testing/TEST_REPORT.md`

**Gate checks:**
- [ ] Test command exits with code 0
- [ ] If `coverage.enabled: true` — measured coverage meets or exceeds `coverage.min_percentage`
- [ ] `sdlc/testing/TEST_REPORT.md` exists and is non-empty

---

### 7.7 Stage: `review`

**Purpose:** The system performs a structured self-review of all changes before the developer authorises a PR.

**Inputs:**
- Git diff of all changes since the pipeline started (scoped to the current branch)
- All prior stage artefacts: `PRD.md`, `ARCH.md`, `TEST_REPORT.md`
- `PRINCIPLES.md`

**LangGraph node behaviour:**
- LLM generates `sdlc/review/REVIEW.md` (schema in §9.4)
- `REVIEW.md` includes: summary of changes, PRD alignment check, PRINCIPLES compliance check, test evidence summary, and a final `recommendation: PASS | FAIL` field
- Stage halts; developer reads `REVIEW.md`
- Developer approves by running `/sdlc pr`
- Developer rejects by running `/sdlc coding` (re-enters the coding loop with review notes as added context)
- Developer may override a `FAIL` recommendation by running `/sdlc pr --force` (requires explicit confirmation prompt)

**Gate checks:**
- [ ] `sdlc/review/REVIEW.md` exists
- [ ] `REVIEW.md` contains a `recommendation:` field with value `PASS` or `FAIL`
- [ ] If recommendation is `FAIL` and developer runs `/sdlc pr` without `--force` → block with error message

---

### 7.8 Stage: `pr`

**Purpose:** Commit all pipeline artefacts and open a structured GitHub Pull Request.

**Inputs:**
- Current git branch
- `sdlc/review/REVIEW.md` (used as PR description body)
- `sdlc/planning/PRD.md` (linked in PR body)

**LangGraph node behaviour:**
- Stages and commits all `sdlc/` artefacts to the current branch
- Constructs a PR body following the template in §9.5
- Executes `gh pr create` with structured title and body
- Captures and stores the returned PR URL in `.sdlc_state.json` under `pr_url`
- Marks pipeline status as `complete`

**Gate checks:**
- [ ] `gh auth status` exits with code 0
- [ ] Current branch is not `main`, `master`, or the configured `github.base_branch`
- [ ] `gh pr create` exits with code 0

**OpenCode output:**
```
[pr] ✓ Pull Request created: https://github.com/owner/repo/pull/42
Pipeline complete. All artefacts committed to sdlc/.
```

---

## 8. OpenCode Integration

### 8.1 Slash Command Definition

**File:** `.opencode/commands/sdlc.md`

```markdown
---
description: Advance the project through the SDLC pipeline.
subtask: true
---

You are the orchestration interface for the [PROJECT_NAME] SDLC pipeline.
Your role is display and relay only — you do not write code or make decisions.

1. Execute the pipeline script for the requested stage:
   !`python3 ./scripts/sdlc_pipeline.py --stage="$ARGUMENTS"`

2. Relay the script's stdout output to the developer verbatim.

3. Do NOT write code, modify files, skip stages, or suggest next steps
   beyond what the script output instructs.

4. If the script exits non-zero, surface the full error output and stop.
```

### 8.2 Command Invocation Reference

| Command | Description |
|---------|-------------|
| `/sdlc planning "<intent>"` | Start the pipeline for a new feature or change |
| `/sdlc ui-design` | Run the optional UI design stage |
| `/sdlc architecture` | Run the architecture stage |
| `/sdlc coding` | Run the coding stage, or re-enter the coding loop |
| `/sdlc testing` | Run the testing stage |
| `/sdlc review` | Run the self-review stage |
| `/sdlc pr` | Submit the GitHub Pull Request |
| `/sdlc pr --force` | Submit PR even when `REVIEW.md` recommendation is `FAIL` |
| `/sdlc status` | Print the current pipeline state from `.sdlc_state.json` |
| `/sdlc reset` | Clear pipeline state and start fresh (requires confirmation) |

### 8.3 Subtask Isolation

Each `/sdlc` invocation MUST use `subtask: true` in the command frontmatter. This guarantees:

- The LangGraph script's output is captured and displayed within the subagent context
- The subagent context window is fully wiped after the command completes
- The main OpenCode chat history contains only developer-level status messages
- Context rot cannot accumulate across pipeline stages

---

## 9. Data Schemas

### 9.1 PRD.md Schema

`sdlc/planning/PRD.md` MUST contain the following H2 sections. Gate validation uses heading detection.

```markdown
## Summary
One paragraph describing the intended change.

## Goals
- Bulleted list of goals.

## Non-Goals
- Bulleted list of explicit exclusions.

## Tasks
- [ ] Task one
- [ ] Task two
(At least one checkbox task is required.)

## Acceptance Criteria
- Bulleted list of verifiable, binary criteria.

## Affected Files
List of files expected to change, or "TBD — to be determined at architecture stage".
```

---

### 9.2 DESIGN.md Schema (Google Stitch)

`sdlc/ui-design/DESIGN.md` MUST conform to the Google Stitch `DESIGN.md` specification.

Reference: https://stitch.withgoogle.com/docs/design-md/overview

The gate checker validates the presence of the following top-level sections at minimum:

- `## Overview`
- `## Components` or `## Screens`

The `## States` section is optional but recommended for interactive components.

---

### 9.3 ARCH.md Schema

`sdlc/architecture/ARCH.md` MUST contain the following H2 sections:

```markdown
## Overview
Brief description of the architectural approach for this change.

## Target Files
| File | Action | Description |
|------|--------|-------------|
| src/example.ts | CREATE | New module for X |
| src/other.ts   | MODIFY | Update Y to support Z |

## Design Decisions
1. Decision one — rationale.
2. Decision two — rationale.

## PRINCIPLES Compliance
| Rule ID | Description | Status |
|---------|-------------|--------|
| ARCH-001 | Hexagonal layers respected | PASS |
| QUAL-001 | All exports typed | PASS |

## Risks
- Risk one, or "None identified".
```

---

### 9.4 REVIEW.md Schema

`sdlc/review/REVIEW.md` MUST contain the following sections:

```markdown
## Change Summary
What changed, derived from the git diff.

## PRD Alignment
Line-by-line check: does the implementation satisfy each task and
acceptance criterion in PRD.md?

## PRINCIPLES Compliance
Any violations found in the final code, with file and line references.
"None found" if clean.

## Test Evidence
Summary of TEST_REPORT.md: pass/fail counts, coverage percentage.

## Recommendation
recommendation: PASS

## Notes
Optional reviewer notes.
```

The `recommendation:` line MUST appear exactly as shown (colon, space, `PASS` or `FAIL`). Gate validation parses this line programmatically.

---

### 9.5 GitHub PR Body Template

The PR body generated by the `pr` stage MUST follow this structure:

```markdown
## Summary
[First paragraph of sdlc/planning/PRD.md]

## Changes
[Bullet list from REVIEW.md § Change Summary]

## Test Evidence
[Test run summary from sdlc/testing/TEST_REPORT.md]

## Review Outcome
[Recommendation line from sdlc/review/REVIEW.md]

## Pipeline Artefacts
- [PRD](sdlc/planning/PRD.md)
- [Architecture](sdlc/architecture/ARCH.md)
- [Review](sdlc/review/REVIEW.md)
- [Test Report](sdlc/testing/TEST_REPORT.md)
```

---

### 9.6 `.sdlc_state.json` Schema

This file is the single source of truth for pipeline runtime state. It MUST be listed in `.gitignore`.

```json
{
  "$schema": "sdlc-state/v1",
  "pipeline_id": "<uuid-v4>",
  "intent": "<original developer intent string>",
  "branch": "<git branch name>",
  "started_at": "<ISO 8601 timestamp>",
  "current_stage": "planning | ui-design | architecture | coding | testing | review | pr | complete",
  "completed_stages": ["planning"],
  "stages": {
    "planning": {
      "status": "complete | in_progress | failed | skipped",
      "completed_at": "<ISO 8601 timestamp>",
      "artefact": "sdlc/planning/PRD.md",
      "gate_results": {
        "prd_exists": true,
        "prd_schema_valid": true,
        "tasks_defined": true
      }
    },
    "ui-design": {
      "status": "skipped",
      "reason": "No UI keywords found in PRD"
    },
    "coding": {
      "status": "complete",
      "iterations": 2,
      "artefact": null,
      "gate_results": {
        "linter_passed": true,
        "build_passed": true,
        "target_files_exist": true
      }
    }
  },
  "pr_url": "<GitHub PR URL, or null>"
}
```

All stage entries follow the same shape. Unknown or future stages MUST be ignored by the parser (forward-compatible).

---

### 9.7 `PRINCIPLES.md` Schema

`PRINCIPLES.md` is a developer-authored file at the project root. It defines project-specific guardrails enforced during the `architecture` and `review` stages. The pipeline ships with a `PRINCIPLES.example.md` as a reference template.

The file MUST follow this schema:

```markdown
# PRINCIPLES

## Project
name: <project name>
language: <primary language, e.g. TypeScript>
framework: <framework, e.g. Next.js, FastAPI, or "none">

## Architecture Rules

### ARCH-001
description: <Human-readable rule description>
severity: error | warning
check: <How to verify — e.g. "no direct DB calls outside /repositories", "all exports are typed">

### ARCH-002
description: ...
severity: ...
check: ...

## Code Quality Rules

### QUAL-001
description: ...
severity: error | warning
check: ...

## Testing Rules

### TEST-001
description: ...
severity: error | warning
check: <e.g. "min coverage: 80%", "all public functions have at least one test">

## Naming Conventions

Free-form markdown describing naming rules for files, functions, classes, and variables.

## Forbidden Patterns

- Pattern one that must never appear in the codebase
- Pattern two
```

**Validation rules:**
- The file MUST contain a `## Project` section and at least one rule to be considered valid
- If `PRINCIPLES.md` is absent, the pipeline emits a warning but does not block execution; PRINCIPLES checks are skipped
- Rules with `severity: error` block the `architecture` and `review` stages if violated
- Rules with `severity: warning` are included in artefacts but do not block stage progression

---

### 9.8 `sdlc.config.json` Schema

`sdlc.config.json` lives at the project root and MUST be committed to the repository.

```json
{
  "$schema": "sdlc-config/v1",
  "default_model": "<model string, e.g. openai/gpt-4o>",
  "stages": {
    "planning":     { "model": "<model string>" },
    "ui-design":    { "model": "<model string>" },
    "architecture": { "model": "<model string>" },
    "coding":       { "model": "<model string>", "max_iterations": 5 },
    "testing":      { "model": "<model string>" },
    "review":       { "model": "<model string>" }
  },
  "commands": {
    "lint":            "<shell command, e.g. npx eslint . --max-warnings 0>",
    "build":           "<shell command, e.g. npm run build>",
    "test":            "<shell command, e.g. npm test -- --coverage>",
    "coverage_report": "<path to coverage summary JSON, or null>"
  },
  "coverage": {
    "enabled": true,
    "min_percentage": 80
  },
  "github": {
    "base_branch": "main"
  },
  "timeouts": {
    "llm_call_seconds":   120,
    "command_seconds":    300
  }
}
```

Any stage omitted from `stages` falls back to `default_model`. The `default_model` field is required.

---

## 10. Repository Structure

```
<project-root>/
│
├── .opencode/
│   └── commands/
│       └── sdlc.md                   # OpenCode slash command definition
│
├── scripts/
│   ├── sdlc_pipeline.py              # LangGraph pipeline entry point
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── planning.py               # planning node
│   │   ├── ui_design.py              # ui-design node
│   │   ├── architecture.py           # architecture node
│   │   ├── coding.py                 # coding loop subgraph
│   │   ├── testing.py                # testing node
│   │   ├── review.py                 # review node
│   │   └── pr.py                     # pr node
│   ├── gates/
│   │   ├── __init__.py
│   │   ├── gate_runner.py            # Executes hard criteria checks per stage
│   │   └── principles_checker.py     # Validates artefacts against PRINCIPLES.md
│   └── utils/
│       ├── __init__.py
│       ├── state.py                  # Read/write .sdlc_state.json
│       ├── git.py                    # Git helpers: diff, branch, commit
│       └── config.py                 # Load and validate sdlc.config.json
│
├── sdlc/                             # Generated artefacts (committed to repo)
│   ├── planning/
│   │   └── PRD.md
│   ├── ui-design/
│   │   └── DESIGN.md
│   ├── architecture/
│   │   └── ARCH.md
│   ├── coding/
│   │   └── ITERATIONS.md             # Written only on coding loop failure
│   ├── testing/
│   │   └── TEST_REPORT.md
│   ├── review/
│   │   └── REVIEW.md
│   └── logs/                         # LLM call logs (committed)
│       └── <stage>_<timestamp>.log
│
├── PRINCIPLES.md                     # Developer-authored guardrails (committed)
├── PRINCIPLES.example.md             # Reference template (committed)
├── sdlc.config.json                  # Pipeline configuration (committed)
├── .sdlc_state.json                  # Pipeline runtime state (gitignored)
├── .gitignore                        # Must include .sdlc_state.json
├── README.md
└── CONTRIBUTING.md
```

`.sdlc_state.json` MUST appear in `.gitignore`. All files under `sdlc/` MUST be committed.

---

## 11. Technical Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Orchestration | LangGraph (Python) | State machine; loop subgraph for coding stage |
| Terminal UI | OpenCode | Slash commands; subtask isolation mode |
| LLM abstraction | LangChain (via LangGraph) | Per-stage model config |
| Git operations | `git` CLI | Branch, diff, commit |
| PR creation | `gh` CLI (GitHub CLI) | `gh pr create` |
| State persistence | JSON flat file | `.sdlc_state.json` |
| Schema validation | Pydantic v2 | Config, state, and artefact validation |
| Runtime | Python 3.11+ | |
| Distribution | `pip install` | PyPI package |

---

## 12. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | The pipeline MUST be fully resumable after a terminal restart with zero state loss |
| NFR-2 | Each stage MUST complete or fail with a clear error within the configured timeout (default: 120s for LLM calls, 300s for commands) |
| NFR-3 | All LLM calls MUST be logged to `sdlc/logs/<stage>_<timestamp>.log` for auditability |
| NFR-4 | No API keys, tokens, or secrets are ever written to disk or included in logs |
| NFR-5 | The `scripts/` directory MUST have ≥80% test coverage |
| NFR-6 | All public Python functions MUST carry type annotations |
| NFR-7 | The project MUST follow semantic versioning and include a `CONTRIBUTING.md` |
| NFR-8 | The tool MUST be installable via `pip install <package-name>` |
| NFR-9 | macOS and Linux are supported targets; Windows support is deferred to a future version |

---

## 13. Error Handling

| Scenario | Behaviour |
|----------|-----------|
| LLM call fails or times out | Retry up to 3 times with exponential backoff; fail the stage with a clear error message after all retries are exhausted |
| Gate check fails | Print the specific failing check; do not advance the pipeline; do not modify `.sdlc_state.json` |
| Coding loop reaches `max_iterations` | Fail the stage; write full iteration log to `sdlc/coding/ITERATIONS.md`; notify the developer |
| `gh` CLI not authenticated | Fail the `pr` stage with: *"Run `gh auth login` and then retry `/sdlc pr`"* |
| `PRINCIPLES.md` not found | Emit a warning at pipeline start; skip all PRINCIPLES checks; do not block execution |
| `sdlc.config.json` missing or invalid | Fail immediately at startup with a Pydantic validation error and a reference to the schema |
| `.sdlc_state.json` missing | Treat as a fresh pipeline; create the file on first stage execution |
| `.sdlc_state.json` corrupted or unparseable | Fail with a clear error; instruct the developer to run `/sdlc reset` |
| Stage invoked out of order | Fail with an error listing completed stages and the expected next stage |

---

## 14. Open Questions

| ID | Question | Priority |
|----|----------|----------|
| OQ-1 | **Project name** — candidates: Forge, Relay, Conductor, Operator, Ralph. To be decided before first public release. | High |
| OQ-2 | **`ui-design` stage** — should the node call the Stitch API directly to produce the `DESIGN.md`, or should it generate a spec that the developer manually runs through the Stitch interface? | Medium |
| OQ-3 | **LLM call log format** — structured JSON (machine-readable, supports future tooling) or plain text (human-readable for quick debugging)? | Low |
| OQ-4 | **`/sdlc reset` archival** — should the command archive the previous pipeline run to `sdlc/archive/<pipeline_id>/` before clearing state, or discard entirely? | Low |
| OQ-5 | **PRINCIPLES.md `check` field** — should rule `check` fields support regex patterns for automated static analysis, or remain free-form text interpreted by the LLM? | Medium |

---

*End of document. Version 0.1.0-draft.*
