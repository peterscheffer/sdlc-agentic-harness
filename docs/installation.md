# SDLC Pipeline Installation Guide

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
- `.opencode/config.json`, `node_modules/` — OpenCode-specific, not pipeline-specific

## Setup Steps After Copy

1. Add `.sdlc_state.json` to `.gitignore`
2. Configure `sdlc.config.json` with the new project's test/lint/build commands and desired models
3. Optionally create `PRINCIPLES.md` with project-specific rules
4. Set environment variables:
   ```bash
   export OPENAI_API_KEY=KEY
   export OPENAI_API_BASE=http://127.0.0.1:11434/v1   # for local models
   ```
5. (Optional) LangSmith observability — create `.env` at project root:
   ```
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=lsv2_pt_...
   LANGSMITH_PROJECT=sdlc-agentic-harness
   ```
   Each LLM call is traced with `stage`, `pipeline_id`, and `iteration` metadata for filtering in the LangSmith UI.
6. Optionally copy `.opencode/commands/sdlc.md` for `/sdlc` slash command support
