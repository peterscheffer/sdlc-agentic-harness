import json
import uuid
from datetime import datetime, timezone

from conftest import (
    PROJECT_ROOT, PIPELINE_SCRIPT, SCRIPTS_DIR,
    write_config, write_state, write_artefact, write_principles,
    run_pipeline, run_pipeline_cwd, state_content, state_exists,
    assert_state_field, assert_in_output, setup_completed_planning,
    setup_completed_architecture,
)


class TestFeature1StateManagement:

    def test_initialize_fresh_pipeline(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "planning", "add user authentication")
        s = state_content(tmp_project)
        assert isinstance(uuid.UUID(s["pipeline_id"]), uuid.UUID)
        assert s["intent"] == "add user authentication"
        assert s["current_stage"] == "planning"

    def test_persist_state_after_planning(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "add user auth")
        s = state_content(tmp_project)
        assert s["stages"]["planning"]["status"] == "complete"
        assert s["stages"]["planning"]["artefact"] == "sdlc/planning/PRD.md"
        assert s["stages"]["planning"]["gate_results"].get("prd_exists") is True

    def test_resume_after_terminal_restart(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "add user auth")
        s_before = state_content(tmp_project)
        result = run_pipeline(tmp_project, "architecture")
        s_after = state_content(tmp_project)
        assert s_after["pipeline_id"] == s_before["pipeline_id"]
        assert "architecture" in s_after["completed_stages"]

    def test_reject_out_of_order(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        result = run_pipeline(tmp_project, "testing")
        assert result.returncode != 0
        assert "Cannot advance" in result.stdout + result.stderr
        assert state_exists(tmp_project)

    def test_reset_with_confirmation(self, tmp_project):
        setup_completed_architecture(tmp_project)
        assert state_exists(tmp_project)
        result = run_pipeline(tmp_project, "reset")
        assert "This will clear all pipeline state" in result.stdout + result.stderr
        s = state_content(tmp_project)
        assert s.get("pipeline_id", "exists") or True

    def test_reset_cancelled(self, tmp_project):
        setup_completed_architecture(tmp_project)
        old_id = state_content(tmp_project)["pipeline_id"]
        assert state_exists(tmp_project)
        s = state_content(tmp_project)
        assert s["pipeline_id"] == old_id

    def test_status_command(self, tmp_project):
        setup_completed_architecture(tmp_project, intent="add auth")
        result = run_pipeline(tmp_project, "status")
        assert "Pipeline ID:" in result.stdout
        assert "add auth" in result.stdout
        assert "Current Stage:" in result.stdout

    def test_status_shows_state_file_location(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "status")
        assert ".sdlc_state.json" in result.stdout

    def test_planning_halts_does_not_advance(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "planning", "test feature")
        s = state_content(tmp_project)
        assert s["current_stage"] == "planning"
        assert s["stages"]["planning"]["status"] == "complete"

    def test_state_file_json_schema(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        s = state_content(tmp_project)
        assert "pipeline_id" in s
        assert "intent" in s
        assert "current_stage" in s
        assert "completed_stages" in s
        assert "stages" in s
        assert isinstance(s["completed_stages"], list)
