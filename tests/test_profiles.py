import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".scripts"))

from utils.config import SDLCConfig, ProfileConfig
from utils.state import SDLCPersistedState
from profiles import (
    PROFILE_REGISTRY, resolve_profile_names, get_profiles,
    validate_profile_names, CLASSIFICATION_DEFAULTS,
)
from profiles.gherkin_bdd import GherkinBddProfile
from profiles.unit_tests import UnitTestsProfile, TEST_CASES_PATH
from profiles.openapi_contract import OpenApiContractProfile


def make_config(**overrides) -> SDLCConfig:
    base = {"default_model": "m"}
    base.update(overrides)
    return SDLCConfig.model_validate(base)


@pytest.fixture
def in_tmp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestRegistryResolution:
    def test_all_profiles_registered(self):
        assert set(PROFILE_REGISTRY) == {"gherkin-bdd", "unit-tests", "openapi-contract", "stitch-ui"}

    def test_override_wins_over_state_and_config(self):
        state = SDLCPersistedState(spec_profiles=["unit-tests"])
        config = make_config(default_profiles=["openapi-contract"])
        assert resolve_profile_names(state, config, ["gherkin-bdd"]) == ["gherkin-bdd"]

    def test_state_wins_over_config(self):
        state = SDLCPersistedState(spec_profiles=["unit-tests"])
        config = make_config(default_profiles=["openapi-contract"])
        assert resolve_profile_names(state, config) == ["unit-tests"]

    def test_config_default_used_when_state_empty(self):
        state = SDLCPersistedState()
        config = make_config(default_profiles=["openapi-contract"])
        assert resolve_profile_names(state, config) == ["openapi-contract"]

    def test_legacy_default_is_gherkin(self):
        state = SDLCPersistedState()
        config = make_config()
        assert resolve_profile_names(state, config) == ["gherkin-bdd"]

    def test_classification_not_auto_applied(self):
        # A recommendation only takes effect once adopted into state.
        state = SDLCPersistedState(solution_classification={
            "type": "api", "recommended_profiles": ["openapi-contract"],
        })
        config = make_config()
        assert resolve_profile_names(state, config) == ["gherkin-bdd"]

    def test_unknown_profile_raises(self):
        state = SDLCPersistedState(spec_profiles=["nonsense"])
        with pytest.raises(ValueError, match="nonsense"):
            resolve_profile_names(state, make_config())

    def test_validate_profile_names_lists_valid(self):
        error = validate_profile_names(["bogus"])
        assert "bogus" in error
        assert "gherkin-bdd" in error

    def test_get_profiles_returns_instances(self):
        state = SDLCPersistedState(spec_profiles=["gherkin-bdd", "unit-tests"])
        profiles = get_profiles(state, make_config())
        assert [p.name for p in profiles] == ["gherkin-bdd", "unit-tests"]

    def test_classification_defaults_cover_all_types(self):
        for t in ("ui", "api", "service", "integration", "data", "mixed"):
            assert CLASSIFICATION_DEFAULTS[t]


class TestGherkinBddProfile:
    def test_parse_and_write_feature_files(self, in_tmp_dir):
        profile = GherkinBddProfile(make_config())
        llm_content = (
            "```requirements-md\n# Reqs\n```\n"
            "---FEATURE_FILE: login.feature---\n"
            "```gherkin\nFeature: Login\n  Scenario: ok\n    Given a\n    When b\n    Then c\n```\n"
            "---FEATURE_FILE: logout.feature---\n"
            "```gherkin\nFeature: Logout\n  Scenario: ok\n    Given a\n    When b\n    Then c\n```\n"
        )
        written = profile.parse_and_write(llm_content)
        assert len(written) == 2
        assert os.path.exists("sdlc/requirements/login.feature")
        content = open("sdlc/requirements/login.feature").read()
        assert content.startswith("Feature: Login")
        assert "```" not in content

    def test_requirements_gate_fails_without_features(self, in_tmp_dir):
        profile = GherkinBddProfile(make_config())
        check = profile.requirements_gate_checks()[0]
        passed, msg = check.run()
        assert not passed

    def test_parse_last_feature_stops_at_its_own_fence(self, in_tmp_dir):
        # Regression: when the LAST ---FEATURE_FILE--- block is followed by
        # other profiles' fenced blocks (test-cases-md, openapi-yaml) in the
        # same LLM response, only that feature's own fenced content must be
        # written — not everything through the end of the message.
        llm_content = (
            "```requirements-md\n# Reqs\n```\n"
            "---FEATURE_FILE: login.feature---\n"
            "```gherkin\nFeature: Login\n  Scenario: ok\n    Given a\n    When b\n    Then c\n```\n"
            "\n---\n\n"
            "```test-cases-md\n# Test Cases\n| ID | Description | Test File | Priority |\n"
            "|----|----|----|----|\n| TC-1 | x | tests/t.py | High |\n```\n"
            "\n---\n\n"
            "```openapi-yaml\nopenapi: 3.0.3\ninfo:\n  title: T\n  version: 1.0.0\npaths: {}\n```\n"
        )
        profile = GherkinBddProfile(make_config())
        written = profile.parse_and_write(llm_content)
        assert written == ["sdlc/requirements/login.feature"]
        content = open("sdlc/requirements/login.feature").read()
        assert content.strip() == (
            "Feature: Login\n  Scenario: ok\n    Given a\n    When b\n    Then c"
        )
        assert "test-cases-md" not in content
        assert "openapi" not in content

    def test_custom_command_skips_runner_preflight(self):
        config = make_config(profiles={"gherkin-bdd": {"command": "echo ok"}})
        profile = GherkinBddProfile(config)
        ok, _ = profile.preflight()
        assert ok
        assert profile.resolve_command() == "echo ok"

    def test_verifier_gate_passes_on_exit_zero(self, in_tmp_dir):
        config = make_config(profiles={"gherkin-bdd": {"command": "exit 0"}})
        profile = GherkinBddProfile(config)
        check = profile.verification_gate_checks()[0]
        assert check.name == "profile_gherkin_bdd_verified"
        passed, _ = check.run()
        assert passed

    def test_verifier_gate_fails_on_nonzero_with_output(self, in_tmp_dir):
        config = make_config(profiles={"gherkin-bdd": {"command": "echo step-undefined; exit 1"}})
        profile = GherkinBddProfile(config)
        passed, msg = profile.verification_gate_checks()[0].run()
        assert not passed
        assert "step-undefined" in msg

    def test_scaffold_targets_python(self, in_tmp_dir, monkeypatch):
        (in_tmp_dir / "pyproject.toml").write_text("")
        os.makedirs("sdlc/requirements", exist_ok=True)
        Path("sdlc/requirements/user-login.feature").write_text("Feature: x")
        profile = GherkinBddProfile(make_config())
        targets = profile.coding_scaffold_targets([])
        assert targets == ["sdlc/requirements/steps/user_login_steps.py"]

    def test_scaffold_targets_java_includes_runner(self, in_tmp_dir):
        (in_tmp_dir / "pom.xml").write_text("<project/>")
        os.makedirs("sdlc/requirements", exist_ok=True)
        Path("sdlc/requirements/user-login.feature").write_text("Feature: x")
        profile = GherkinBddProfile(make_config())
        targets = profile.coding_scaffold_targets([])
        assert "src/test/java/sdlc/steps/UserLoginSteps.java" in targets
        assert "src/test/java/sdlc/RunCucumberTest.java" in targets

    def test_scaffold_targets_ts(self, in_tmp_dir):
        (in_tmp_dir / "package.json").write_text("{}")
        (in_tmp_dir / "tsconfig.json").write_text("{}")
        os.makedirs("sdlc/requirements", exist_ok=True)
        Path("sdlc/requirements/user-login.feature").write_text("Feature: x")
        profile = GherkinBddProfile(make_config())
        targets = profile.coding_scaffold_targets([])
        assert targets == ["sdlc/requirements/steps/user-login.steps.ts"]
        assert "ts-node/register" in profile.resolve_command()

    def test_java_verifier_command(self, in_tmp_dir):
        (in_tmp_dir / "pom.xml").write_text("<project/>")
        profile = GherkinBddProfile(make_config())
        assert profile.resolve_command() == "mvn -q test"


class TestUnitTestsProfile:
    LLM_CONTENT = (
        "```requirements-md\n# Reqs\n```\n"
        "```test-cases-md\n"
        "# Test Cases\n\n"
        "| ID | Description | Test File | Priority |\n"
        "|----|-------------|-----------|----------|\n"
        "| TC-1 | Login works | tests/test_login.py | High |\n"
        "| TC-2 | Logout works | tests/test_logout.py | Low |\n"
        "```\n"
    )

    def test_parse_and_write(self, in_tmp_dir):
        profile = UnitTestsProfile(make_config())
        written = profile.parse_and_write(self.LLM_CONTENT)
        assert written == [TEST_CASES_PATH]
        assert "TC-1" in open(TEST_CASES_PATH).read()

    def test_scaffold_targets_from_test_file_column(self, in_tmp_dir):
        profile = UnitTestsProfile(make_config())
        profile.parse_and_write(self.LLM_CONTENT)
        targets = profile.coding_scaffold_targets([])
        assert targets == ["tests/test_login.py", "tests/test_logout.py"]

    def test_gate_fails_without_cases(self, in_tmp_dir):
        profile = UnitTestsProfile(make_config())
        passed, _ = profile.requirements_gate_checks()[0].run()
        assert not passed

    def test_gate_passes_with_cases(self, in_tmp_dir):
        profile = UnitTestsProfile(make_config())
        profile.parse_and_write(self.LLM_CONTENT)
        passed, msg = profile.requirements_gate_checks()[0].run()
        assert passed
        assert "2 test case(s)" in msg

    def test_default_command_python(self, in_tmp_dir):
        (in_tmp_dir / "pyproject.toml").write_text("")
        profile = UnitTestsProfile(make_config())
        assert profile.resolve_command() == "python3 -m pytest tests -q"

    def test_vitest_command(self, in_tmp_dir):
        (in_tmp_dir / "package.json").write_text('{"devDependencies":{"vitest":"1"}}')
        profile = UnitTestsProfile(make_config())
        assert profile.resolve_command() == "npx vitest run tests"


class TestOpenApiContractProfile:
    LLM_CONTENT = (
        "```requirements-md\n# Reqs\n```\n"
        "```openapi-yaml\n"
        "openapi: 3.0.3\n"
        "info:\n  title: T\n  version: 1.0.0\n"
        "paths:\n  /health:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        "```\n"
    )

    def test_parse_and_write(self, in_tmp_dir):
        profile = OpenApiContractProfile(make_config())
        written = profile.parse_and_write(self.LLM_CONTENT)
        assert written == ["sdlc/requirements/openapi.yaml"]

    def test_gate_passes_on_valid_doc(self, in_tmp_dir):
        profile = OpenApiContractProfile(make_config())
        profile.parse_and_write(self.LLM_CONTENT)
        passed, _ = profile.requirements_gate_checks()[0].run()
        assert passed

    def test_gate_fails_without_paths(self, in_tmp_dir):
        profile = OpenApiContractProfile(make_config())
        os.makedirs("sdlc/requirements", exist_ok=True)
        Path("sdlc/requirements/openapi.yaml").write_text("openapi: 3.0.3\n")
        passed, msg = profile.requirements_gate_checks()[0].run()
        assert not passed

    def test_preflight_fails_without_server_config(self, in_tmp_dir):
        profile = OpenApiContractProfile(make_config())
        ok, msg = profile.preflight()
        assert not ok
        # actionable message either way (schemathesis missing or config missing)
        assert "sdlc.config.json" in msg

    def test_custom_command_runs_verbatim(self, in_tmp_dir):
        config = make_config(profiles={"openapi-contract": {"command": "exit 0"}})
        profile = OpenApiContractProfile(config)
        ok, _ = profile.preflight()
        assert ok
        result = profile.run_verifier()
        assert result["exit_code"] == 0
