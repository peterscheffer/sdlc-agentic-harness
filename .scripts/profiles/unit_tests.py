import os
import re

from gates.gate_runner import GateCheck
from utils.toolchain import (
    is_java, is_js, java_test_command, detect_js_test_framework,
)
from profiles.base import SpecProfile, command_available

TEST_CASES_PATH = "sdlc/requirements/TEST_CASES.md"
TEST_CASES_BLOCK = re.compile(r"```test-cases-md\s*\n(.*?)```", re.DOTALL)


class UnitTestsProfile(SpecProfile):
    """Requirements expressed as enumerated test cases; verified by running
    the spec-derived tests with the project's test framework."""

    name = "unit-tests"
    display_name = "Unit/Integration Tests"

    # --- toolchain -----------------------------------------------------

    def resolve_runner(self) -> str:
        if self.profile_config.runner:
            return self.profile_config.runner
        if is_java(self.language):
            return "junit"
        if is_js(self.language):
            return detect_js_test_framework(self.project_root)
        return "pytest"

    def tests_dir(self) -> str:
        if self.profile_config.tests_dir:
            return self.profile_config.tests_dir
        if is_java(self.language):
            return "src/test/java"
        return "tests"

    # --- requirements stage ----------------------------------------------

    def spec_prompt_fragment(self) -> str:
        runner = self.resolve_runner()
        return (
            "### Test Case Specification (TEST_CASES.md)\n"
            "Enumerate every requirement as a concrete, automatable test case.\n"
            "- Output a Markdown table with EXACTLY these columns: "
            "ID | Description | Test File | Priority\n"
            "- Description: a single verifiable behaviour (input/state → expected outcome)\n"
            f"- Test File: the {runner} test file that will implement the case, "
            f"under `{self.tests_dir()}/` (group related cases in the same file)\n"
            "- Priority: High/Medium/Low\n\n"
            "Test case output format:\n"
            "```test-cases-md\n"
            "# Test Cases\n\n"
            "| ID | Description | Test File | Priority |\n"
            "|----|-------------|-----------|----------|\n"
            "| TC-1 | ... | ... | High |\n"
            "```\n"
        )

    def parse_and_write(self, llm_content: str) -> list[str]:
        match = TEST_CASES_BLOCK.search(llm_content)
        if not match:
            return []
        os.makedirs(os.path.dirname(TEST_CASES_PATH), exist_ok=True)
        with open(TEST_CASES_PATH, "w") as f:
            f.write(match.group(1).strip() + "\n")
        return [TEST_CASES_PATH]

    def spec_artifacts(self) -> list[str]:
        return [TEST_CASES_PATH] if os.path.exists(TEST_CASES_PATH) else []

    def requirements_gate_checks(self) -> list[GateCheck]:
        def _check() -> tuple[bool, str]:
            if not os.path.exists(TEST_CASES_PATH):
                return False, f"{TEST_CASES_PATH} does not exist"
            cases = self._parse_test_cases()
            if not cases:
                return False, f"{TEST_CASES_PATH} contains no test case rows"
            return True, f"{len(cases)} test case(s) specified"
        return [GateCheck("test_cases_defined", "TEST_CASES.md has at least one case", _check)]

    def _parse_test_cases(self) -> list[dict]:
        if not os.path.exists(TEST_CASES_PATH):
            return []
        with open(TEST_CASES_PATH) as f:
            content = f.read()
        cases = []
        for line in content.split("\n"):
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) >= 4 and parts[0] and parts[0] not in ("ID",) \
                    and not all(c in "-: " for c in parts[0]):
                cases.append({
                    "id": parts[0], "description": parts[1],
                    "test_file": parts[2], "priority": parts[3],
                })
        return cases

    # --- coding stage ------------------------------------------------------

    def coding_scaffold_targets(self, arch_targets: list[str]) -> list[str]:
        targets = []
        for case in self._parse_test_cases():
            tf = case["test_file"].strip("`")
            if tf and tf not in targets:
                targets.append(tf)
        return targets

    def coding_prompt_fragment(self) -> str:
        return (
            f"Implement EVERY test case listed in {TEST_CASES_PATH} as a real "
            f"{self.resolve_runner()} test in the Test File named for that case. "
            "Tests must exercise the real application code and assert the expected "
            f"outcome. They will be executed with `{self.resolve_command()}` and must pass."
        )

    # --- verification -------------------------------------------------------

    def resolve_command(self) -> str:
        if self.profile_config.command:
            return self.profile_config.command
        runner = self.resolve_runner()
        if runner == "junit":
            return java_test_command(self.language)
        if runner == "jest":
            return f"npx jest {self.tests_dir()}"
        if runner == "vitest":
            return f"npx vitest run {self.tests_dir()}"
        return f"python3 -m pytest {self.tests_dir()} -q"

    def preflight(self) -> tuple[bool, str]:
        if self.profile_config.command:
            return True, "Custom verifier command configured"
        runner = self.resolve_runner()
        probes = {
            "pytest": ("python3 -m pytest --version",
                       "pytest is not installed. Install with: pip install pytest, "
                       "or set profiles.\"unit-tests\".command in sdlc.config.json"),
            "jest": ("npx --no-install jest --version",
                     "jest is not installed. Install with: npm install --save-dev jest, "
                     "or set profiles.\"unit-tests\".command in sdlc.config.json"),
            "vitest": ("npx --no-install vitest --version",
                       "vitest is not installed. Install with: npm install --save-dev vitest, "
                       "or set profiles.\"unit-tests\".command in sdlc.config.json"),
            "junit": ("mvn -v" if self.language == "java-maven" else "gradle -v",
                      "Build tool not available for JUnit. Ensure mvn/gradle is on PATH, "
                      "or set profiles.\"unit-tests\".command in sdlc.config.json"),
        }
        probe, message = probes.get(runner, (None, None))
        if probe is None:
            return False, (
                f"Unknown unit-tests runner '{runner}'. "
                "Valid runners: pytest, jest, vitest, junit."
            )
        if command_available(probe):
            return True, f"{runner} is available"
        return False, message
