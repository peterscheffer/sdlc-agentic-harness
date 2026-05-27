import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / ".scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from conftest import (
    write_config, write_state, write_artefact, run_pipeline, state_content,
    setup_completed_planning, setup_completed_architecture, setup_completed_coding,
    setup_completed_testing, BASE_CONFIG, PRD_WITHOUT_UI,
)

SAMPLE_TEMPLATE = """# Product Requirements Document
## Test Feature — One-line descriptor

| Field | Value |
|-------|-------|
| **Version** | 0.1.0-draft |
| **Status** | Draft |
| **Last Updated** | 2025-01-01 |

---

## 1. Executive Summary

Test project.

---

## 2. Problem Statement

Nothing.

---

## 3. Goals

| ID | Goal |
|----|------|
| G1 | Test goal |

---

## 4. Non-Goals

| ID | Non-Goal |
|----|----------|
| NG1 | Out of scope |

---

## 5. User Persona

**Developer**

---

## 6. System Architecture Overview

Simple.

---

## 7. Stage / Feature Definitions

### 7.1 Overview

| Order | ID | Required | Output |
|-------|----|----------|--------|
| 1 | `feature` | Yes | `output` |

---

## 8. External Integrations

None.

---

## 9. Data Schemas

TBD.

---

## 10. Repository Structure

TBD.

---

## 11. Technical Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Runtime | Python | |

---

## 12. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Works |

---

## 13. Error Handling

None.

---

## 14. Open Questions

None.

---

*End of document. Version 0.1.0-draft.*
"""


class TestPDRUpdaterHelpers:

    def test_bump_version_increment_minor(self, tmp_project):
        from utils.prd_updater import _bump_prd_version
        result = _bump_prd_version(SAMPLE_TEMPLATE)
        assert "0.2.0-draft" in result
        assert "0.1.0-draft" not in result

    def test_bump_version_updates_date(self, tmp_project):
        from utils.prd_updater import _bump_prd_version
        result = _bump_prd_version(SAMPLE_TEMPLATE)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in result

    def test_bump_version_multiple_calls(self, tmp_project):
        from utils.prd_updater import _bump_prd_version
        v1 = _bump_prd_version(SAMPLE_TEMPLATE)
        assert "0.2.0-draft" in v1
        v2 = _bump_prd_version(v1)
        assert "0.3.0-draft" in v2
        v3 = _bump_prd_version(v2)
        assert "0.4.0-draft" in v3

    def test_parse_target_files_from_arch(self, tmp_project):
        from utils.prd_updater import _parse_target_files
        arch_content = """## Overview
Test.

## Target Files
| File | Action | Description |
|------|--------|-------------|
| src/feature.py | CREATE | New feature |
| src/utils.py | MODIFY | Update utils |

## Design Decisions
None.
"""
        arch_path = str(tmp_project / "sdlc/architecture/ARCH.md")
        (tmp_project / "sdlc/architecture").mkdir(parents=True, exist_ok=True)
        (tmp_project / "sdlc/architecture/ARCH.md").write_text(arch_content)
        files = _parse_target_files(arch_path)
        assert "src/feature.py" in files
        assert "src/utils.py" in files
        assert len(files) == 2

    def test_parse_target_files_missing_arch(self, tmp_project):
        from utils.prd_updater import _parse_target_files
        files = _parse_target_files("nonexistent/ARCH.md")
        assert files == []


class TestPDRUpdaterStageArtefacts:

    def test_get_artefact_coding_no_files(self, tmp_project):
        from utils.prd_updater import _get_stage_artefact_content
        state = _make_test_state(tmp_project)
        content = _get_stage_artefact_content(state, "coding")
        assert content == ""

    def test_get_artefact_coding_with_files(self, tmp_project):
        from utils.prd_updater import _get_stage_artefact_content
        arch_path = tmp_project / "sdlc/architecture/ARCH.md"
        arch_path.parent.mkdir(parents=True, exist_ok=True)
        arch_path.write_text("""## Target Files
| File | Action |
|------|--------|
| src/feature.py | CREATE |
""")
        (tmp_project / "src").mkdir(parents=True, exist_ok=True)
        (tmp_project / "src/feature.py").write_text("# code")
        state = _make_test_state(tmp_project)
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_project))
            content = _get_stage_artefact_content(state, "coding")
        finally:
            os.chdir(old_cwd)
        assert "src/feature.py" in content
        assert "# code" in content

    def test_get_artefact_from_state_artefact_path(self, tmp_project):
        from utils.prd_updater import _get_stage_artefact_content
        from utils.state import SDLCPersistedState, StageEntry
        (tmp_project / "sdlc/ui-design").mkdir(parents=True, exist_ok=True)
        (tmp_project / "sdlc/ui-design/DESIGN.md").write_text("# DESIGN\n\n## Overview\nTest UI")
        state = _make_test_state(tmp_project)
        state.stages["ui-design"].artefact = "sdlc/ui-design/DESIGN.md"
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_project))
            content = _get_stage_artefact_content(state, "ui-design")
        finally:
            os.chdir(old_cwd)
        assert "Test UI" in content


class TestPDRUpdaterNoUpdate:

    def test_no_update_when_prd_missing(self, tmp_project):
        from utils.prd_updater import update_prd_if_needed
        config = _make_config(tmp_project)
        state = _make_test_state(tmp_project)
        result = update_prd_if_needed(state, config, "ui-design", "")
        assert result is False

    def test_no_update_when_no_artefact_and_no_context(self, tmp_project):
        from utils.prd_updater import update_prd_if_needed
        write_config(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITHOUT_UI)
        setup_completed_planning(tmp_project)
        config = _make_config(tmp_project)
        state = _make_test_state(tmp_project)
        result = update_prd_if_needed(state, config, "ui-design", "")
        assert result is False

    def test_no_update_in_mock_mode(self, tmp_project):
        write_config(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", SAMPLE_TEMPLATE)
        setup_completed_planning(tmp_project)
        (tmp_project / "sdlc/ui-design").mkdir(parents=True, exist_ok=True)
        (tmp_project / "sdlc/ui-design/DESIGN.md").write_text("# DESIGN\n\n## Overview\nTest")
        result = run_pipeline(tmp_project, "ui-design")
        assert result.returncode == 0

    def test_planning_stage_skips_prd_update(self, tmp_project):
        write_config(tmp_project)
        (tmp_project / "sdlc/templates").mkdir(parents=True, exist_ok=True)
        (tmp_project / "sdlc/templates/PRD.md").write_text(SAMPLE_TEMPLATE)
        result = run_pipeline(tmp_project, "planning", "test feature")
        assert result.returncode == 0
        s = state_content(tmp_project)
        assert s["stages"]["planning"]["status"] == "complete"


def _make_test_state(tmp_project) -> "SDLCPersistedState":
    from utils.state import SDLCPersistedState, StageEntry
    state = SDLCPersistedState(
        pipeline_id=str(uuid.uuid4()),
        intent="test",
        branch="main",
        started_at=datetime.now(timezone.utc).isoformat(),
        current_stage="planning",
    )
    state.stages["planning"].status = "complete"
    state.stages["planning"].artefact = "sdlc/planning/PRD.md"
    state.completed_stages.append("planning")
    return state


def _make_config(tmp_project) -> "SDLCConfig":
    from utils.config import SDLCConfig
    return SDLCConfig(**BASE_CONFIG)
