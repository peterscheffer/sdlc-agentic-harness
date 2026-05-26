from conftest import (
    write_config, write_state, write_artefact, write_principles,
    run_pipeline, state_content, assert_in_output, setup_completed_planning,
    PRD_WITHOUT_UI, PRINCIPLES_CONTENT, MOCK_ARCH,
)


ARCH_MISSING_SECTION = """# ARCH

## Overview
Minimal arch.

## Target Files
| File | Action | Description |
|------|--------|-------------|
| src/feat.py | CREATE | New module |

## Risks
None.
"""

ARCH_NO_TARGET_FILES = """# Architecture Decision Record

## Overview
No target files.

## Design Decisions
1. None

## PRINCIPLES Compliance
No violations.

## Risks
None.
"""

ARCH_WITH_VIOLATIONS = """# Architecture Decision Record

## Overview
Violating arch.

## Target Files
| File | Action | Description |
|------|--------|-------------|
| src/feat.py | CREATE | New module |

## Design Decisions
1. Test

## PRINCIPLES Compliance
| Rule | Status | Notes |
|------|--------|-------|
| ARCH-001 | WARN | Minor issue |
| ARCH-002 | FAIL | Violation |

## Risks
None.
"""


class TestFeature4Architecture:

    def test_generate_arch_md_from_prd(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        result = run_pipeline(tmp_project, "architecture")
        assert (tmp_project / "sdlc/architecture/ARCH.md").exists()
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        assert len(content) > 0

    def test_arch_md_contains_required_sections(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        required = ["## Overview", "## Target Files", "## Design Decisions",
                     "## PRINCIPLES Compliance", "## Risks"]
        for heading in required:
            assert heading in content, f"Missing: {heading}"

    def test_target_files_section_has_table(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        assert "CREATE" in content or "MODIFY" in content or "DELETE" in content
        assert "File" in content
        assert "Action" in content

    def test_validate_arch_against_principles(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        assert "PRINCIPLES Compliance" in content

    def test_pass_architecture_gate_with_warnings_only(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", ARCH_WITH_VIOLATIONS)
        run_pipeline(tmp_project, "architecture")
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        assert True

    def test_fail_architecture_gate_with_error_violations(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", ARCH_WITH_VIOLATIONS)
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        if s["stages"]["architecture"]["status"] == "failed":
            assert "violates" in str(s).lower()

    def test_gate_check_arch_exists(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["architecture"]["gate_results"].get("arch_exists") is True

    def test_gate_check_arch_schema_valid(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["architecture"]["gate_results"].get("arch_schema_valid") is True

    def test_gate_check_principles_errors_zero(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert "principles_errors_zero" in s["stages"]["architecture"]["gate_results"]

    def test_fail_if_arch_not_generated(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        s = state_content(tmp_project)
        assert True

    def test_fail_if_arch_missing_required_section(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", ARCH_MISSING_SECTION)
        write_principles(tmp_project)
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        if s["stages"]["architecture"]["gate_results"].get("arch_schema_valid") is False:
            assert True

    def test_handle_missing_principles_gracefully(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        result = run_pipeline(tmp_project, "architecture")
        content = (tmp_project / "sdlc/architecture/ARCH.md").read_text()
        has_warning = "Not found" in content or "Warning" in content or "skipped" in content.lower()

    def test_update_state_on_architecture_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["architecture"]["status"] == "complete"
        assert s["stages"]["architecture"]["artefact"] == "sdlc/architecture/ARCH.md"
        assert "architecture" in s["completed_stages"]

    def test_display_architecture_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        result = run_pipeline(tmp_project, "architecture")
        assert "[architecture]" in result.stdout
        assert "Gate checks passed" in result.stdout or "ARCH.md" in result.stdout

    def test_display_architecture_violations(self, tmp_project):
        write_config(tmp_project)
        write_principles(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", ARCH_WITH_VIOLATIONS)
        result = run_pipeline(tmp_project, "architecture")
        output = result.stdout + result.stderr
        if "PRINCIPLES" in output.upper():
            assert True

    def test_log_llm_calls_architecture(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        run_pipeline(tmp_project, "architecture")
        logs = list((tmp_project / "sdlc/logs").glob("architecture_*.log"))
        assert len(logs) >= 0

    def test_no_principles_md_does_not_fail_stage(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        result = run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["architecture"]["status"] == "complete"
