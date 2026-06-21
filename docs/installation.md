# SDLC Pipeline Installation Guide

## Setting Up This Repository for Development

Clone this repository and install dependencies to run the SDLC pipeline locally:

```bash
git clone https://github.com/peterscheffer/sdlc-agentic-harness.git
cd sdlc-agentic-harness
npm install  # Install OpenCode plugin support (in .opencode/)
pip install langchain-openai pydantic  # Install Python dependencies
```

## Environment Setup

Set up environment variables for LLM access:

```bash
export OPENAI_API_KEY=your_api_key
export OPENAI_API_BASE=http://127.0.0.1:11434/v1   # for local models (e.g., Ollama)
```

Optional — enable LangSmith tracing by creating `.env` at project root:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=sdlc-agentic-harness
```

Each LLM call is traced with `stage`, `pipeline_id`, and `iteration` metadata for filtering in the LangSmith UI.

---

## Integrating This Pipeline Into Other Projects

Copy these files into a new project to bring the LangGraph SDLC pipeline with you.

## Required — The Pipeline Itself

| Path | Purpose |
|------|---------|
| `.scripts/` | The entire directory — `langgraph_sdlc.py` + `utils/`, `nodes/`, `gates/` |
| `sdlc.config.json` | Pipeline configuration (models, commands, timeouts) |

## Required — Dependencies

- Add `.sdlc_state.json` to `.gitignore`

```
pip install langchain-openai pydantic
```

## Optional — But Recommended

| Path | Purpose |
|------|---------|
| `.opencode/commands/sdlc.md` | Enables `/sdlc` slash command in OpenCode |
| `PRINCIPLES.md` | Project guardrails validated during architecture stage |
| `tests/` | Test suite covering all 330 Gherkin scenarios |

## Not Needed

- `.sdlc_state.json` — auto-generated, gitignored, recreated per project
- `sdlc/` artefact directory — auto-generated during pipeline runs
- `.opencode/node_modules/` — auto-installed via `npm install`, gitignored (do not commit)
- `.env` (secrets) — create locally, do not commit (see `.env.example` for template)

## Setup Steps After Copy

1. Add `.sdlc_state.json` to `.gitignore`
2. Configure `sdlc.config.json` with the new project's test/lint/build commands and desired models
3. Optionally create `PRINCIPLES.md` with project-specific rules
4. Set environment variables (see Environment Setup section above)
5. (Optional) Optionally copy `.opencode/commands/sdlc.md` for `/sdlc` slash command support

## Running Tests

The test suite covers all SDLC pipeline stages with 216 meaningful tests:

```bash
python -m pytest tests/ -q              # Run all tests
python -m pytest tests/ -v              # Verbose output
python -m pytest tests/test_coding.py   # Run specific test file
python -m pytest -m "not todo" tests/   # Skip incomplete tests
```

The test suite validates:
- Pipeline stage execution (planning, coding, architecture, testing, review, PR)
- Error handling and recovery
- State management across pipeline runs
- Gate checks and validation rules
- Configuration handling
