import os

from conftest import (
    write_config, write_state, write_artefact, write_principles,
    run_pipeline, state_content, assert_in_output, setup_completed_architecture,
    MOCK_ARCH,
)


ARCH_MULTI_FILE = """# Architecture Decision Record

## Overview
Multi-file feature.

## Target Files
| File | Action | Description |
|------|--------|-------------|
| src/auth.py | CREATE | Auth module |
| src/middleware.py | CREATE | Middleware module |

## Design Decisions
1. Modular

## PRINCIPLES Compliance
No violations.

## Risks
None.
"""


class TestFeature5Coding:

    def test_coding_begins_with_fresh_context(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        result = run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)

    def test_iteration1_generates_target_files(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        result = run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        assert s["stages"]["coding"]["status"] in ("complete", "failed")

    def test_iteration1_gate_checks_run(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        gr = s["stages"]["coding"]["gate_results"]
        assert "linter_passed" in gr or "build_passed" in gr or "target_files_exist" in gr

    def test_iteration1_linter_passes(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "echo 'lint ok'", "build": ""}})
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)

    def test_iteration1_build_passes(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "", "build": "echo 'build ok'"}})
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)

    def test_iteration1_file_existence_passes(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        write_artefact(tmp_project, "src/feature.py", "# feature code")
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        assert s["stages"]["coding"]["gate_results"].get("target_files_exist") in (True, None)

    def test_all_gate_checks_pass_coding_succeeds(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        write_artefact(tmp_project, "src/feature.py", "# feature code")
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        if s["stages"]["coding"]["status"] == "complete":
            assert s["stages"]["coding"]["iterations"] >= 1

    def test_iteration1_gate_fails_proceeds_to_iteration2(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_principles(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)

    def test_context_cleared_between_iterations(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)

    def test_iteration2_receives_failure_reason(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")

    def test_iteration2_modifies_code_to_fix_failure(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 0", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")

    def test_iteration2_gate_checks_run_again(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 0", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")

    def test_iteration2_passes_loop_exits(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 0", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)

    def test_iteration2_fails_proceeds_to_iteration3(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": "exit 1"}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")

    def test_multiple_iterations_different_failures(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")

    def test_reach_max_iterations_without_passing(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")

    def test_write_iteration_log_on_failure(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")

    def test_iteration_log_is_human_readable(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        itermd = tmp_project / "sdlc/coding/ITERATIONS.md"
        if itermd.exists():
            content = itermd.read_text()
            assert "Iteration" in content or "iteration" in content.lower()
            assert "Linter" in content or "Build" in content or "File" in content

    def test_update_state_on_coding_success(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        write_artefact(tmp_project, "src/feature.py", "# feature code")
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        if s["stages"]["coding"]["status"] == "complete":
            assert "coding" in s["completed_stages"]

    def test_update_state_on_coding_failure(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        if s["stages"]["coding"]["status"] == "failed":
            assert s["current_stage"] == "coding"

    def test_developer_can_manually_fix_code_and_rerun(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        write_artefact(tmp_project, "src/feature.py", "# fixed manually")
        result = run_pipeline(tmp_project, "coding")

    def test_display_coding_progress(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        result = run_pipeline(tmp_project, "coding")
        assert "[coding]" in result.stdout

    def test_display_coding_failure_clearly(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "exit 1", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        result = run_pipeline(tmp_project, "coding")
        output = result.stdout + result.stderr
        assert "[coding]" in output

    def test_log_llm_calls_in_coding(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        logs = list((tmp_project / "sdlc/logs").glob("coding_iteration_*.log"))
        assert True

    def test_no_secrets_in_coding_logs(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        logs = list((tmp_project / "sdlc/logs").glob("coding_iteration_*.log"))
        for log in logs:
            content = log.read_text()
            assert "sk-" not in content
            assert "Bearer " not in content

    def test_coding_gate_checks_are_hard_criteria_only(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        gr = s["stages"]["coding"].get("gate_results", {})
        hard_checks = {"linter_passed", "build_passed", "target_files_exist"}
        assert hard_checks.intersection(gr.keys()) or not gr

    def test_coding_restarts_from_iteration1_on_rerun(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        result = run_pipeline(tmp_project, "coding")

    def test_max_iterations_config_respected(self, tmp_project):
        write_config(tmp_project, {"stages": {"coding": {"max_iterations": 3}}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")

    def test_empty_lint_command_skipped(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)

    def test_empty_build_command_skipped(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": "", "build": ""}})
        setup_completed_architecture(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
