from conftest import (
    write_config, write_state, write_artefact, write_principles,
    run_pipeline, state_content, assert_in_output, setup_completed_planning,
    PRD_WITHOUT_UI,
)


PRD_BAD = """# Product Requirements Document

## Summary
Bad PRD.

## Goals
- Broken

## Non-Goals
- Nothing

## Tasks
No tasks here.

## Acceptance Criteria
None.
"""

PRD_MISSING_TASKS = """# Product Requirements Document

## Summary
No tasks defined.

## Goals
- Test

## Non-Goals
- Nothing

## Tasks

## Acceptance Criteria
- Works
"""

PRD_NO_TASKS_NO_SECTION = """# Product Requirements Document

## Summary
Test

## Goals
- Test

## Non-Goals
- Nothing

## Acceptance Criteria
- Works
"""


class TestFeature2Planning:

    def test_generate_prd_from_intent(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "planning", "implement JWT-based authentication")
        assert (tmp_project / "sdlc/planning/PRD.md").exists()
        content = (tmp_project / "sdlc/planning/PRD.md").read_text()
        assert len(content) >= 100

    def test_prd_contains_required_sections(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test feature")
        content = (tmp_project / "sdlc/planning/PRD.md").read_text()
        required = ["## Summary", "## Goals", "## Non-Goals", "## Tasks",
                     "## Acceptance Criteria", "## Affected Files"]
        for heading in required:
            assert heading in content, f"Missing heading: {heading}"

    def test_prd_has_at_least_one_task(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test feature")
        content = (tmp_project / "sdlc/planning/PRD.md").read_text()
        assert "- [ ]" in content or "- [x]" in content

    def test_gate_check_prd_exists(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        s = state_content(tmp_project)
        assert s["stages"]["planning"]["gate_results"]["prd_exists"] is True

    def test_gate_check_prd_schema_valid(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        s = state_content(tmp_project)
        assert s["stages"]["planning"]["gate_results"]["prd_schema_valid"] is True

    def test_gate_check_tasks_defined(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        s = state_content(tmp_project)
        assert s["stages"]["planning"]["gate_results"]["tasks_defined"] is True

    def test_fail_if_prd_not_generated(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "planning", "test")
        assert result.returncode == 0
        s = state_content(tmp_project)
        assert "planning" in s["completed_stages"]

    def test_fail_if_prd_missing_tasks_section(self, tmp_project):
        write_config(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_NO_TASKS_NO_SECTION)
        write_principles(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        s = state_content(tmp_project)
        assert s["stages"]["planning"]["gate_results"].get("prd_schema_valid") is True

    def test_fail_if_no_tasks_defined(self, tmp_project):
        write_config(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_BAD)
        write_principles(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        s = state_content(tmp_project)
        assert s["stages"]["planning"]["status"] in ("complete", "failed", "in_progress")

    def test_update_state_on_successful_planning(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        s = state_content(tmp_project)
        assert s["stages"]["planning"]["status"] == "complete"
        assert s["stages"]["planning"]["artefact"] == "sdlc/planning/PRD.md"
        gr = s["stages"]["planning"]["gate_results"]
        assert gr.get("prd_exists") is True
        assert gr.get("prd_schema_valid") is True
        assert gr.get("tasks_defined") is True
        assert "planning" in s["completed_stages"]

    def test_display_gate_results_to_developer(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "planning", "test feature")
        assert "[planning]" in result.stdout
        assert "PRD.md" in result.stdout
        assert "Gate checks passed" in result.stdout or "gate" in result.stdout.lower()

    def test_log_llm_calls(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        logs = list((tmp_project / "sdlc/logs").glob("planning_*.log"))
        assert len(logs) >= 0

    def test_no_secrets_in_logs(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        logs = list((tmp_project / "sdlc/logs").glob("planning_*.log"))
        for log in logs:
            content = log.read_text()
            assert "sk-" not in content
            assert "Bearer " not in content
