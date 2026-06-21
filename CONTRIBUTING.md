# Contributing to SDLC Agentic Harness

Thanks for your interest in contributing! This project is a LangGraph-style SDLC
orchestration engine that drives code changes through structured, gate-verified
stages.

## Development setup

```bash
git clone https://github.com/peterscheffer/sdlc-agentic-harness.git
cd sdlc-agentic-harness

# Dependencies
pip install langchain-openai pydantic python-dotenv

# Configuration
cp .env.example .env        # then fill in your own values
```

The pipeline talks to any OpenAI-compatible endpoint (local Ollama, OpenRouter,
or OpenAI). See [docs/installation.md](docs/installation.md) for the full setup.

## Running the tests

```bash
python -m pytest tests/ -q
```

The suite covers the Gherkin scenarios for every stage and runs without real API
calls (it uses a mock LLM). You can force the mock explicitly with
`SDLC_USE_MOCK_LLM=1`.

## Making changes

1. Fork the repo and create a topic branch off `main`.
2. Keep changes focused; match the style and structure of the surrounding code.
3. Add or update tests for any behavior change.
4. Make sure `python -m pytest tests/ -q` passes before opening a PR.
5. Review [docs/PRINCIPLES.md](docs/PRINCIPLES.md) — it documents the
   architecture rules the pipeline itself enforces.

## Opening a pull request

- Describe **what** changed and **why**.
- Link any related issue.
- Keep the PR scoped to a single concern where possible.

## Reporting bugs / requesting features

Open an issue with steps to reproduce (for bugs) or a clear use case (for
features). For security issues, see [SECURITY.md](SECURITY.md) instead.
