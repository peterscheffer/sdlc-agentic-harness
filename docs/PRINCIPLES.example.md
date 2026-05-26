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
