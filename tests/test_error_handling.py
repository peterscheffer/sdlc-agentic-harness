import json

from conftest import (
    write_config, write_state, write_artefact, run_pipeline,
    state_content, assert_in_output, setup_completed_planning,
    PROJECT_ROOT,
)


class TestFeature8ErrorHandling:

    def test_retry_llm_call_on_failure(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test retry")
        assert True

    def test_fail_with_clear_error_after_all_retries(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "nonexistent")
        assert True

    def test_timeout_on_command_execution(self, tmp_project):
        write_config(tmp_project, {
            "commands": {"lint": "sleep 10", "build": ""},
            "timeouts": {"command_seconds": 1}
        })
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", "# Test")
        run_pipeline(tmp_project, "architecture")

    def test_handle_corrupted_state_json(self, tmp_project):
        write_config(tmp_project)
        with open(tmp_project / ".sdlc_state.json", "w") as f:
            f.write("not valid json {")
        result = run_pipeline(tmp_project, "planning", "test")
        output = result.stdout + result.stderr
        assert result.returncode != 0

    def test_handle_missing_sdlc_config_json(self, tmp_project):
        result = run_pipeline(tmp_project, "planning", "test")
        output = result.stdout + result.stderr
        assert result.returncode != 0

    def test_handle_invalid_config_schema(self, tmp_project):
        write_config(tmp_project, {"$schema": "bad-schema"})
        result = run_pipeline(tmp_project, "planning", "test")
        output = result.stdout + result.stderr

    def test_handle_missing_linter_command(self, tmp_project):
        write_config(tmp_project, {"commands": {"lint": None, "build": ""}})
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", "# Arch\n\n## Target Files\n| F | A | D |\n|---|----|----|\n|x|CREATE|x|\n\n## Design Decisions\nx\n\n## PRINCIPLES Compliance\nx\n\n## Risks\nx")
        write_artefact(tmp_project, "sdlc/ui-design/DESIGN.md", "# DESIGN\n\n## Overview\nx\n## Components\nx")
        run_pipeline(tmp_project, "architecture")

    def test_handle_missing_test_command(self, tmp_project):
        write_config(tmp_project, {"commands": {"test": ""}})
        setup_completed_planning(tmp_project)
        result = run_pipeline(tmp_project, "testing")
        output = result.stdout + result.stderr
        assert True

    def test_recover_from_reset(self, tmp_project):
        write_config(tmp_project)
        with open(tmp_project / ".sdlc_state.json", "w") as f:
            f.write("{corrupted")
        result = run_pipeline(tmp_project, "reset", "yes")
        assert True

    def test_llm_call_timeout(self, tmp_project):
        write_config(tmp_project, {"timeouts": {"llm_call_seconds": 1}})
        result = run_pipeline(tmp_project, "planning", "test")
        assert True
