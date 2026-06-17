# PRINCIPLES

## Project

name: MoM  
language: Python framework: none

## Architecture Rules

### ARCH-001

description: The pipeline follows a strict sequential SDLC with LangGraph state machine orchestration.
severity: error
check: All stage transitions are validated against STAGE_ORDER and gate checks must pass before advancing.

### ARCH-002

description: Pipeline state is persisted to .sdlc_state.json and survives terminal restarts.
severity: error
check: State is read from .sdlc_state.json on every invocation and written back after completion.

## Code Quality Rules

### QUAL-001

description: All public Python functions carry type annotations.
severity: warning
check: All public functions have type hints.

### QUAL-002

description: LLM calls are logged to sdlc/logs/ for auditability.
severity: error
check: Every LLM invocation writes a log file with timestamp, model, and token counts.

## Testing Rules

### TEST-001

description: Each stage has hard gate checks that must pass before the pipeline advances.
severity: error
check: Gate checks run and must all pass for stage completion.

## Forbidden Patterns

- Hardcoded API keys or secrets in source code or log files
- Skipping gate checks or stage transitions
- Writing secrets to .sdlc_state.json or log files

