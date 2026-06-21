import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "todo: test not yet implemented or blocked by known issues")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / ".scripts"
PIPELINE_SCRIPT = SCRIPTS_DIR / "langgraph_sdlc.py"

BASE_CONFIG = {
    "$schema": "sdlc-config/v1",
    "default_model": "openai/gpt-4o",
    "stages": {
        "planning": {"model": "openai/gpt-4o"},
        "ui-design": {"model": "openai/gpt-4o"},
        "architecture": {"model": "openai/gpt-4o"},
        "coding": {"model": "openai/gpt-4o", "max_iterations": 5},
        "testing": {"model": "openai/gpt-4o"},
        "review": {"model": "openai/gpt-4o"},
    },
    "commands": {
        "lint": "",
        "build": "",
        "test": "echo 'test ok'",
        "coverage_report": None,
    },
    "coverage": {"enabled": False, "min_percentage": 80},
    "github": {"base_branch": "main"},
    "timeouts": {"llm_call_seconds": 120, "command_seconds": 300},
}

PRINCIPLES_CONTENT = """# PRINCIPLES

## Project
name: TestProject
language: Python
framework: none

## Architecture Rules

### ARCH-001
description: Pipeline follows strict sequential SDLC
severity: error
check: All stage transitions validated

### ARCH-002
description: State persisted to .sdlc_state.json
severity: error
check: State read/written on every invocation

## Code Quality Rules

### QUAL-001
description: All public functions have type annotations
severity: warning
check: Public functions have type hints
"""

PRD_WITH_UI = """# Product Requirements Document

## Summary
Add a new dashboard view with user settings form for the application.

## Goals
- Deliver the feature
- Maintain existing functionality

## Non-Goals
- Performance optimization

## Tasks
- [ ] Design and implement the feature
- [ ] Write tests

## Acceptance Criteria
- Feature works as described
- All tests pass

## Affected Files
TBD
"""

PRD_WITHOUT_UI = """# Product Requirements Document

## Summary
Add backend API authentication for the application.

## Goals
- Deliver the feature
- Maintain existing functionality

## Non-Goals
- Performance optimization

## Tasks
- [ ] Design and implement the feature
- [ ] Write tests

## Acceptance Criteria
- Feature works as described
- All tests pass

## Affected Files
TBD
"""

MOCK_ARCH = """# Architecture Decision Record

## Overview
Architecture for test feature.

## Target Files
| File | Action | Description |
|------|--------|-------------|
| src/feature.py | CREATE | New feature module |

## Design Decisions
1. Modular design

## PRINCIPLES Compliance
No PRINCIPLES violations.

## Risks
None identified.
"""

MOCK_REVIEW_PASS = """## Change Summary
Files modified: src/feature.py (+10, -2)

## PRD Alignment
All tasks addressed.

## PRINCIPLES Compliance
No violations found.

## Test Evidence
All tests passing.

## Recommendation
recommendation: PASS

## Notes
None
"""

MOCK_REVIEW_FAIL = """## Change Summary
Files modified: src/feature.py (+10, -2)

## PRD Alignment
Critical task not addressed.

## PRINCIPLES Compliance
Error violation found.

## Test Evidence
Tests failing.

## Recommendation
recommendation: FAIL

## Notes
Fix critical issues before PR.
"""


@pytest.fixture
def mock_llm_env(monkeypatch):
    monkeypatch.setenv("SDLC_USE_MOCK_LLM", "1")
    yield


@pytest.fixture
def tmp_project(tmp_path, mock_llm_env):
    project = tmp_path / "project"
    project.mkdir()
    yield project


def write_config(project: Path, overrides: Optional[dict] = None):
    config = _deep_copy_config(BASE_CONFIG)
    if overrides:
        config = _deep_merge(config, overrides)
    with open(project / "sdlc.config.json", "w") as f:
        json.dump(config, f, indent=2)


def _deep_copy_config(cfg):
    import copy
    return copy.deepcopy(cfg)


def _deep_merge(base, overrides):
    result = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def write_principles(project: Path, content: Optional[str] = None):
    with open(project / "PRINCIPLES.md", "w") as f:
        f.write(content or PRINCIPLES_CONTENT)


def write_state(project: Path, state: dict):
    with open(project / ".sdlc_state.json", "w") as f:
        json.dump(state, f, indent=2)


def write_artefact(project: Path, path: str, content: str):
    full_path = project / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)


def _build_pipeline_args(stage_or_cmd: str, feature: str = "", force: bool = False):
    if stage_or_cmd in ("status", "reset"):
        return [stage_or_cmd]
    args = ["--stage", stage_or_cmd]
    if feature:
        args += ["--feature", feature]
    if force:
        args += ["--force"]
    return args


def run_pipeline(project: Path, stage_or_cmd: str = "", feature: str = "",
                 force: bool = False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["SDLC_USE_MOCK_LLM"] = "1"
    args = _build_pipeline_args(stage_or_cmd, feature, force)
    result = subprocess.run(
        [sys.executable, str(PIPELINE_SCRIPT)] + args,
        capture_output=True, text=True, timeout=60,
        env=env, cwd=str(project),
    )
    return result


def run_pipeline_cwd(stage_or_cmd: str = "", feature: str = "",
                     force: bool = False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["SDLC_USE_MOCK_LLM"] = "1"
    args = _build_pipeline_args(stage_or_cmd, feature, force)
    result = subprocess.run(
        [sys.executable, str(PIPELINE_SCRIPT)] + args,
        capture_output=True, text=True, timeout=60,
        env=env,
    )
    return result


def state_content(project: Path) -> dict:
    with open(project / ".sdlc_state.json") as f:
        return json.load(f)


def state_exists(project: Path) -> bool:
    return (project / ".sdlc_state.json").exists()


def assert_state_field(project: Path, field: str, expected):
    s = state_content(project)
    value = s
    for part in field.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = None
            break
    assert value == expected, f"Expected state.{field} = {expected!r}, got {value!r}"


def assert_in_output(result: subprocess.CompletedProcess, text: str):
    assert text in result.stdout or text in result.stderr, (
        f"Expected {text!r} in output.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )


def setup_completed_planning(project: Path, intent: str = "test feature"):
    write_config(project)
    write_artefact(project, "sdlc/planning/PRD.md", PRD_WITHOUT_UI)
    state = {
        "pipeline_id": str(uuid.uuid4()),
        "intent": intent,
        "branch": "main",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "current_stage": "planning",
        "completed_stages": ["planning"],
        "stages": {
            s: {"status": "not_started", "completed_at": None, "artefact": None,
                "reason": None, "iterations": None, "coverage_percent": None,
                "recommendation": None,
                "gate_results": {}}
            for s in ["planning", "ui-design", "architecture", "requirements", "coding",
                      "testing", "review", "pr", "complete"]
        },
        "pr_url": None,
    }
    state["stages"]["planning"]["status"] = "complete"
    state["stages"]["planning"]["artefact"] = "sdlc/planning/PRD.md"
    state["stages"]["planning"]["gate_results"] = {
        "prd_exists": True, "prd_schema_valid": True, "tasks_defined": True
    }
    write_state(project, state)


def setup_completed_architecture(project: Path, intent: str = "test feature"):
    setup_completed_planning(project, intent)
    write_artefact(project, "sdlc/ui-design/DESIGN.md", "# DESIGN\n\n## Overview\nTest")
    write_artefact(project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
    s = state_content(project)
    s["current_stage"] = "architecture"
    s["completed_stages"] = ["planning", "ui-design", "architecture"]
    s["stages"]["ui-design"]["status"] = "complete"
    s["stages"]["ui-design"]["artefact"] = "sdlc/ui-design/DESIGN.md"
    s["stages"]["architecture"]["status"] = "complete"
    s["stages"]["architecture"]["artefact"] = "sdlc/architecture/ARCH.md"
    write_state(project, s)


def setup_completed_requirements(project: Path, intent: str = "test feature"):
    setup_completed_architecture(project, intent)
    write_artefact(project, "sdlc/requirements/REQUIREMENTS.md",
                  "# Requirements\n\n## Overview\nTest\n\n## Functional Requirements\n| ID | Desc |\n| FR-1 | Test |\n\n## Non-Functional Requirements\n| ID | Desc |\n| NFR-1 | Test |\n\n## Behavioural Requirements\n| ID | Scenario | Expected |\n| BR-1 | Test | OK |")
    s = state_content(project)
    s["current_stage"] = "requirements"
    s["completed_stages"] = ["planning", "ui-design", "architecture", "requirements"]
    s["stages"]["requirements"]["status"] = "complete"
    s["stages"]["requirements"]["artefact"] = "sdlc/requirements/REQUIREMENTS.md"
    write_state(project, s)


def setup_completed_coding(project: Path, intent: str = "test feature"):
    setup_completed_architecture(project, intent)
    write_artefact(project, "src/feature.py", "# feature code")
    s = state_content(project)
    s["current_stage"] = "coding"
    s["completed_stages"] = ["planning", "ui-design", "architecture", "requirements", "coding"]
    s["stages"]["requirements"]["status"] = "complete"
    s["stages"]["requirements"]["artefact"] = "sdlc/requirements/REQUIREMENTS.md"
    s["stages"]["coding"]["status"] = "complete"
    s["stages"]["coding"]["iterations"] = 1
    s["stages"]["coding"]["gate_results"] = {
        "linter_passed": True, "build_passed": True, "target_files_exist": True
    }
    write_state(project, s)


def setup_completed_testing(project: Path, intent: str = "test feature"):
    setup_completed_coding(project, intent)
    write_artefact(project, "sdlc/testing/TEST_REPORT.md", "# Test Report\n\nAll tests passed.")
    s = state_content(project)
    s["current_stage"] = "testing"
    s["completed_stages"] = ["planning", "ui-design", "architecture", "requirements", "coding", "testing"]
    s["stages"]["testing"]["status"] = "complete"
    s["stages"]["testing"]["artefact"] = "sdlc/testing/TEST_REPORT.md"
    s["stages"]["testing"]["gate_results"] = {
        "tests_passed": True, "test_report_exists": True, "report_not_empty": True
    }
    write_state(project, s)


def setup_completed_review(project: Path, intent: str = "test feature",
                           recommendation: str = "PASS"):
    setup_completed_testing(project, intent)
    review_content = MOCK_REVIEW_PASS if recommendation == "PASS" else MOCK_REVIEW_FAIL
    write_artefact(project, "sdlc/review/REVIEW.md", review_content)
    s = state_content(project)
    s["current_stage"] = "review"
    s["completed_stages"] = ["planning", "ui-design", "architecture", "requirements", "coding",
                              "testing", "review"]
    s["stages"]["review"]["status"] = "complete"
    s["stages"]["review"]["artefact"] = "sdlc/review/REVIEW.md"
    s["stages"]["review"]["recommendation"] = recommendation
    s["stages"]["review"]["gate_results"] = {
        "review_exists": True, "recommendation_present": True
    }
    write_state(project, s)


