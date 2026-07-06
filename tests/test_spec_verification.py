"""Integration tests for spec-profile verification and dark-factory mode."""
import json
import os
import subprocess
import sys

from conftest import (
    PIPELINE_SCRIPT, write_config, write_artefact, state_content,
    setup_completed_requirements, setup_completed_coding, run_pipeline,
    MOCK_ARCH,
)


def run_harness(project, *args):
    env = os.environ.copy()
    env["SDLC_USE_MOCK_LLM"] = "1"
    return subprocess.run(
        [sys.executable, str(PIPELINE_SCRIPT)] + list(args),
        capture_output=True, text=True, timeout=120,
        env=env, cwd=str(project),
    )


class TestMultiProfileRequirements:
    def test_all_three_profiles_write_artifacts(self, tmp_project):
        write_config(tmp_project, {
            "default_profiles": ["gherkin-bdd", "unit-tests", "openapi-contract"],
        })
        r = run_harness(tmp_project, "--stage", "planning", "--feature", "an API service")
        assert r.returncode == 0, r.stdout
        run_harness(tmp_project, "--stage", "ui-design")
        run_harness(tmp_project, "--stage", "architecture")
        r = run_harness(tmp_project, "--stage", "requirements")
        assert r.returncode == 0, r.stdout
        assert (tmp_project / "sdlc/requirements/user-authentication.feature").exists()
        assert (tmp_project / "sdlc/requirements/TEST_CASES.md").exists()
        assert (tmp_project / "sdlc/requirements/openapi.yaml").exists()
        s = state_content(tmp_project)
        assert s["spec_profiles"] == ["gherkin-bdd", "unit-tests", "openapi-contract"]

    def test_context_footer_overrides_config(self, tmp_project):
        write_config(tmp_project)  # config default: gherkin-bdd
        run_harness(tmp_project, "--stage", "planning", "--feature", "a thing")
        run_harness(tmp_project, "--stage", "ui-design")
        run_harness(tmp_project, "--stage", "architecture")
        ctx = tmp_project / "ctx.md"
        ctx.write_text("Discussion...\n\nSPEC_PROFILES: unit-tests\n")
        r = run_harness(tmp_project, "--stage", "requirements", "--context", str(ctx))
        assert r.returncode == 0, r.stdout
        s = state_content(tmp_project)
        assert s["spec_profiles"] == ["unit-tests"]
        assert (tmp_project / "sdlc/requirements/TEST_CASES.md").exists()
        assert not (tmp_project / "sdlc/requirements/user-authentication.feature").exists()


class TestCodingVerifierLoop:
    def test_verifier_failure_fails_stage_with_detail(self, tmp_project):
        setup_completed_requirements(tmp_project)
        # write_config after setup: the setup helpers reset the config
        write_config(tmp_project, {
            "stages": {"coding": {"max_iterations": 2}},
            "profiles": {"gherkin-bdd": {"command": "echo undefined-step-error; exit 1"}},
        })
        write_artefact(tmp_project, "sdlc/requirements/login.feature", "Feature: Login")
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        r = run_harness(tmp_project, "--stage", "coding")
        s = state_content(tmp_project)
        assert s["stages"]["coding"]["status"] == "failed"
        assert s["stages"]["coding"]["gate_results"]["profile_gherkin_bdd_verified"] is False
        # runner output surfaces in the printed failure detail
        assert "undefined-step-error" in r.stdout

    def test_preflight_failure_short_circuits(self, tmp_project):
        setup_completed_requirements(tmp_project)
        write_config(tmp_project, {
            "profiles": {"gherkin-bdd": {"command": None, "runner": "bogus-runner"}},
        })
        write_artefact(tmp_project, "sdlc/architecture/ARCH.md", MOCK_ARCH)
        r = run_harness(tmp_project, "--stage", "coding")
        s = state_content(tmp_project)
        assert s["stages"]["coding"]["status"] == "failed"
        assert "preflight" in s["stages"]["coding"]["reason"].lower()
        # no iterations were burned
        assert s["stages"]["coding"]["iterations"] is None


class TestTestingProfileVerification:
    def test_verifier_pass_completes_stage(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        write_artefact(tmp_project, "sdlc/requirements/login.feature", "Feature: Login")
        r = run_harness(tmp_project, "--stage", "testing")
        assert r.returncode == 0, r.stdout
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] == "complete"
        assert s["stages"]["testing"]["gate_results"]["profile_gherkin_bdd_verified"] is True
        report = (tmp_project / "sdlc/testing/TEST_REPORT.md").read_text()
        assert "Spec Verification: Gherkin BDD" in report

    def test_verifier_failure_fails_stage(self, tmp_project):
        setup_completed_coding(tmp_project)
        write_config(tmp_project, {
            "profiles": {"gherkin-bdd": {"command": "exit 1"}},
        })
        write_artefact(tmp_project, "sdlc/requirements/login.feature", "Feature: Login")
        run_harness(tmp_project, "--stage", "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] == "failed"
        assert s["stages"]["testing"]["gate_results"]["profile_gherkin_bdd_verified"] is False

    def test_no_spec_artifacts_is_lenient(self, tmp_project):
        # Legacy pipeline with no .feature files: verifier is skipped, not failed.
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        r = run_harness(tmp_project, "--stage", "testing")
        assert r.returncode == 0, r.stdout
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] == "complete"

    def test_all_profiles_must_pass(self, tmp_project):
        setup_completed_coding(tmp_project)
        write_config(tmp_project, {
            "default_profiles": ["gherkin-bdd", "unit-tests"],
            "profiles": {
                "gherkin-bdd": {"command": "exit 0"},
                "unit-tests": {"command": "exit 1"},
            },
        })
        write_artefact(tmp_project, "sdlc/requirements/login.feature", "Feature: Login")
        write_artefact(tmp_project, "sdlc/requirements/TEST_CASES.md",
                       "| ID | Description | Test File | Priority |\n"
                       "|----|----|----|----|\n| TC-1 | x | tests/t.py | High |")
        run_harness(tmp_project, "--stage", "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] == "failed"
        assert s["stages"]["testing"]["gate_results"]["profile_gherkin_bdd_verified"] is True
        assert s["stages"]["testing"]["gate_results"]["profile_unit_tests_verified"] is False


class TestDarkFactory:
    def test_auto_accept_runs_pipeline_unattended(self, tmp_project):
        write_config(tmp_project, {
            "profiles": {
                "gherkin-bdd": {"command": "echo ok"},
                "unit-tests": {"command": "echo ok"},
            },
        })
        r = run_harness(tmp_project, "--stage", "planning",
                        "--feature", "add a dashboard UI", "--auto-accept")
        assert r.returncode == 0, r.stdout
        s = state_content(tmp_project)
        assert s["auto_accept"] is True
        # classification (mock: mixed → gherkin-bdd, unit-tests) was auto-adopted
        assert s["spec_profiles"] == ["gherkin-bdd", "unit-tests"]
        assert s["solution_classification"]["type"] == "mixed"
        # pipeline advanced unattended at least through testing and review;
        # pr legitimately fails in the sandbox (no gh auth / feature branch)
        for stage in ["planning", "ui-design", "architecture", "requirements",
                      "coding", "testing", "review"]:
            assert stage in s["completed_stages"], (
                f"{stage} not completed. stdout tail: {r.stdout[-2000:]}")

    def test_profiles_flag_overrides(self, tmp_project):
        write_config(tmp_project, {
            "profiles": {"unit-tests": {"command": "echo ok"}},
        })
        r = run_harness(tmp_project, "--stage", "planning",
                        "--feature", "a service", "--profiles", "unit-tests")
        assert r.returncode == 0, r.stdout
        s = state_content(tmp_project)
        assert s["spec_profiles"] == ["unit-tests"]

    def test_unknown_profiles_flag_rejected(self, tmp_project):
        write_config(tmp_project)
        r = run_harness(tmp_project, "--stage", "planning",
                        "--feature", "x", "--profiles", "made-up")
        assert r.returncode != 0
        assert "made-up" in r.stdout


class TestLegacyStateCompat:
    def test_legacy_state_without_new_fields_loads(self, tmp_project):
        write_config(tmp_project)
        setup_completed_requirements(tmp_project)
        # strip the new fields to simulate a pre-profile state file
        s = state_content(tmp_project)
        for key in ("spec_profiles", "solution_classification", "auto_accept"):
            s.pop(key, None)
        with open(tmp_project / ".sdlc_state.json", "w") as f:
            json.dump(s, f)
        r = run_harness(tmp_project, "status")
        assert r.returncode == 0, r.stdout
