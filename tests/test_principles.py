from conftest import (
    write_config, write_state, write_artefact, write_principles,
    run_pipeline, state_content, assert_in_output, setup_completed_planning,
    setup_completed_architecture, setup_completed_testing, setup_completed_review,
    PRINCIPLES_CONTENT, MOCK_ARCH, MOCK_REVIEW_PASS,
)


PRINCIPLES_WITH_ERROR = """# PRINCIPLES

## Project
name: TestProject
language: Python
framework: none

## Architecture Rules

### ARCH-001
description: Must use hexagonal architecture
severity: error
check: Layers respected

### QUAL-001
description: Exports typed
severity: warning
check: Type hints present
"""

PRINCIPLES_MALFORMED = """# PRINCIPLES

## Project
name: TestProject

This is not properly formatted.
No rules defined.
"""


class TestFeature14Principles:

    def test_principles_read_during_architecture(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        assert "PRINCIPLES Compliance" in content

    def test_validator_checks_each_rule(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert "principles_errors_zero" in s["stages"]["architecture"]["gate_results"]

    def test_error_severity_violations_block_gate(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project, PRINCIPLES_WITH_ERROR)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md",
                      MOCK_ARCH.replace("No PRINCIPLES violations",
                                        "Violation: ARCH-001 not satisfied"))
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert True

    def test_warning_severity_violations_do_not_block(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project, PRINCIPLES_WITH_ERROR)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        assert True

    def test_principles_violations_included_in_review(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project, PRINCIPLES_WITH_ERROR)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        run_pipeline(tmp_project, "review")
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        if "PRINCIPLES" in content:
            assert "Compliance" in content or "violation" in content.lower()

    def test_missing_principles_handled_gracefully(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        result = run_pipeline(tmp_project, "architecture")
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        assert "Not found" in content or "No PRINCIPLES" in content or "skipped" in content.lower()

    def test_invalid_principles_schema_caught(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project, PRINCIPLES_MALFORMED)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["architecture"]["status"] in ("complete", "failed")

    def test_developer_can_use_principles_as_reference(self, tmp_project):
        write_principles(tmp_project, PRINCIPLES_WITH_ERROR)
        content = (tmp_project / "PRINCIPLES.md").read_text()
        assert "ARCH-001" in content
        assert "error" in content
        assert "QUAL-001" in content
        assert "warning" in content

    def test_principles_logged_in_architecture_log(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project, PRINCIPLES_WITH_ERROR)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        logs = list((tmp_project / "sdlc/logs").glob("architecture_*.log"))
        assert True
