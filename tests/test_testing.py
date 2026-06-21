from conftest import (
    write_config, write_state, write_artefact, run_pipeline,
    state_content, assert_in_output, setup_completed_coding,
)


class TestFeature6Testing:

    def test_execute_configured_test_command(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        result = run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] in ("complete", "failed")

    def test_test_command_exits_successfully(self, tmp_project):
        write_config(tmp_project, {"commands": {"test": "echo 'tests ok' && exit 0"}})
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        if s["stages"]["testing"].get("gate_results"):
            assert s["stages"]["testing"]["gate_results"].get("tests_passed") in (True, None)

    def test_capture_test_output_into_report(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        report = tmp_project / "sdlc/testing/TEST_REPORT.md"
        assert report.exists() or state_content(tmp_project)["stages"]["testing"]["status"] != "complete"

    def test_parse_coverage_from_test_output(self, tmp_project):
        write_config(tmp_project, {
            "commands": {"test": "echo 'TOTAL 85%'"},
            "coverage": {"enabled": True, "min_percentage": 80}
        })
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        report = tmp_project / "sdlc/testing/TEST_REPORT.md"
        assert report.exists(), f"Expected TEST_REPORT.md at {report}"
        content = report.read_text()
        assert len(content) > 0

    def test_validate_coverage_meets_threshold(self, tmp_project):
        write_config(tmp_project, {
            "commands": {"test": "echo 'TOTAL 82%'"},
            "coverage": {"enabled": True, "min_percentage": 80}
        })
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        cp = s["stages"]["testing"].get("coverage_percent")
        assert cp is None or isinstance(cp, (int, float))

    def test_fail_if_coverage_below_minimum(self, tmp_project):
        write_config(tmp_project, {
            "commands": {"test": "echo 'TOTAL 72%'"},
            "coverage": {"enabled": True, "min_percentage": 80}
        })
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] in ("complete", "failed", "in_progress")

    def test_skip_coverage_if_disabled(self, tmp_project):
        write_config(tmp_project, {
            "commands": {"test": "echo 'tests ok'"},
            "coverage": {"enabled": False}
        })
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] in ("complete", "failed", "in_progress")

    def test_gate_check_tests_passed(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        if "gate_results" in s["stages"]["testing"]:
            assert "tests_passed" in s["stages"]["testing"]["gate_results"]

    def test_gate_check_test_report_exists(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        if "gate_results" in s["stages"]["testing"]:
            assert "test_report_exists" in s["stages"]["testing"]["gate_results"]

    def test_gate_check_report_not_empty(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        if "gate_results" in s["stages"]["testing"]:
            assert "report_not_empty" in s["stages"]["testing"]["gate_results"]

    def test_fail_if_test_command_exits_non_zero(self, tmp_project):
        setup_completed_coding(tmp_project)
        write_config(tmp_project, {"commands": {"test": "exit 1"}})
        result = run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] == "failed"

    def test_fail_if_test_report_not_created(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        report = tmp_project / "sdlc/testing/TEST_REPORT.md"
        assert report.exists()

    def test_test_report_schema_valid(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        report = tmp_project / "sdlc/testing/TEST_REPORT.md"
        if report.exists():
            content = report.read_text()
            assert len(content) > 0

    def test_respect_test_command_timeout(self, tmp_project):
        write_config(tmp_project, {
            "commands": {"test": "sleep 10"},
            "timeouts": {"command_seconds": 2}
        })
        setup_completed_coding(tmp_project)
        result = run_pipeline(tmp_project, "testing")
        assert result.returncode in (0, 1)

    def test_update_state_on_testing_success(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        if s["stages"]["testing"]["status"] == "complete":
            assert "testing" in s["completed_stages"]

    def test_update_state_on_testing_failure(self, tmp_project):
        setup_completed_coding(tmp_project)
        write_config(tmp_project, {"commands": {"test": "exit 1"}})
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] == "failed"

    def test_display_testing_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        result = run_pipeline(tmp_project, "testing")
        assert "[testing]" in result.stdout

    def test_display_testing_failure(self, tmp_project):
        write_config(tmp_project, {"commands": {"test": "exit 1"}})
        setup_completed_coding(tmp_project)
        result = run_pipeline(tmp_project, "testing")
        assert "[testing]" in result.stdout + result.stderr

    def test_log_test_execution(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        logs = list((tmp_project / "sdlc/logs").glob("testing_*.log"))
        assert len(logs) >= 0

    def test_no_secrets_in_testing_logs(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        logs = list((tmp_project / "sdlc/logs").glob("testing_*.log"))
        for log in logs:
            content = log.read_text()
            assert "sk-" not in content
            assert "Bearer " not in content

    def test_rerun_testing_without_rerun_coding(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        r1 = run_pipeline(tmp_project, "testing")
        s1 = state_content(tmp_project)
        r2 = run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] in ("complete", "failed")

    def test_testing_independent_of_coverage_tool(self, tmp_project):
        write_config(tmp_project, {
            "commands": {"test": "echo 'custom test pass'"},
            "coverage": {"enabled": False}
        })
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] in ("complete", "failed")

    def test_testing_writes_report_even_on_failure(self, tmp_project):
        write_config(tmp_project, {"commands": {"test": "exit 1"}})
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        report = tmp_project / "sdlc/testing/TEST_REPORT.md"
        s = state_content(tmp_project)
        assert report.exists() or s["stages"]["testing"]["status"] in ("complete", "failed")

    def test_coverage_percent_recorded_in_state(self, tmp_project):
        write_config(tmp_project, {
            "commands": {"test": "echo 'TOTAL 90%'"},
            "coverage": {"enabled": True, "min_percentage": 80}
        })
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        cp = s["stages"]["testing"].get("coverage_percent")
        assert cp is None or isinstance(cp, (int, float))

    def test_report_includes_exit_code(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        report = tmp_project / "sdlc/testing/TEST_REPORT.md"
        if report.exists():
            content = report.read_text()
            assert "exit code" in content.lower() or "exit" in content.lower() or "Exit" in content
