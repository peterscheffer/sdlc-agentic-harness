import glob
import os
import re

from gates.gate_runner import GateCheck
from utils.toolchain import (
    LANG_PYTHON, LANG_TS, is_java, is_js, java_test_command,
)
from profiles.base import SpecProfile, command_available

FEATURE_DIR = "sdlc/requirements"
FEATURE_DELIMITER = r'^---FEATURE_FILE:\s*([\w\-]+\.feature)---\s*$'
FIRST_FENCED_BLOCK = re.compile(r'```(?:\w+)?\s*\n(.*?)```', re.DOTALL)


class GherkinBddProfile(SpecProfile):
    """Gherkin feature files verified by actually running a BDD runner
    (behave / cucumber-js / cucumber-jvm) — pass/fail is the runner's
    exit code."""

    name = "gherkin-bdd"
    display_name = "Gherkin BDD"

    # --- toolchain -----------------------------------------------------

    def resolve_runner(self) -> str:
        if self.profile_config.runner:
            return self.profile_config.runner
        if is_java(self.language):
            return "cucumber-jvm"
        if is_js(self.language):
            return "cucumber-js"
        return "behave"

    def steps_dir(self) -> str:
        if self.profile_config.steps_dir:
            return self.profile_config.steps_dir
        runner = self.resolve_runner()
        if runner == "cucumber-jvm":
            return "src/test/java/sdlc/steps"
        # behave discovers steps/ adjacent to the feature files;
        # cucumber-js gets the same directory via --require.
        return os.path.join(FEATURE_DIR, "steps")

    # --- requirements stage ----------------------------------------------

    def spec_prompt_fragment(self) -> str:
        return (
            "### Gherkin Feature Files (one per feature area)\n"
            "- Create separate `.feature` files for each distinct feature area\n"
            "- Each file MUST contain valid Gherkin syntax\n"
            "- Each file MUST have a minimum of: Feature, Scenario, Given, When, Then\n"
            "- Scenarios must be concrete and executable: every Given/When/Then will be "
            "bound to a real step definition and run by a BDD runner, so avoid vague or "
            "unobservable steps\n"
            "- Use this delimiter between files: `---FEATURE_FILE: <name>.feature---`\n"
            "- File names should be kebab-case, e.g. `user-authentication.feature`\n\n"
            "Feature file output format:\n"
            "---FEATURE_FILE: <name>.feature---\n"
            "```gherkin\n"
            "[Gherkin content here]\n"
            "```\n"
        )

    def parse_and_write(self, llm_content: str) -> list[str]:
        os.makedirs(FEATURE_DIR, exist_ok=True)
        segments = re.split(FEATURE_DELIMITER, llm_content, flags=re.MULTILINE)
        written = []
        i = 0
        while i < len(segments):
            segment = segments[i].strip()
            if segment.endswith(".feature") and i + 1 < len(segments):
                code_block = segments[i + 1].strip()
                # The segment after the LAST feature-file marker runs to the end
                # of the LLM response, so it may contain other profiles' fenced
                # blocks (test-cases-md, openapi-yaml) appended after this one's
                # closing fence. Extract only the FIRST fenced block, not the
                # whole remaining segment.
                fence_match = FIRST_FENCED_BLOCK.search(code_block)
                if fence_match:
                    code_content = fence_match.group(1).strip()
                    filepath = os.path.join(FEATURE_DIR, segment)
                    with open(filepath, "w") as f:
                        f.write(code_content)
                    written.append(filepath)
                    i += 2
                    continue
            i += 1
        return written

    def spec_artifacts(self) -> list[str]:
        return sorted(glob.glob(os.path.join(FEATURE_DIR, "*.feature")))

    def requirements_gate_checks(self) -> list[GateCheck]:
        def _check() -> tuple[bool, str]:
            files = self.spec_artifacts()
            if not files:
                return False, f"No .feature files found in {FEATURE_DIR}/"
            for f in files:
                if os.path.getsize(f) == 0:
                    return False, f"Feature file {f} is empty"
            return True, f"{len(files)} feature file(s) found"
        return [GateCheck("feature_files_exist", "At least one .feature file exists", _check)]

    # --- coding stage ------------------------------------------------------

    def coding_scaffold_targets(self, arch_targets: list[str]) -> list[str]:
        targets = []
        runner = self.resolve_runner()
        for feature_path in self.spec_artifacts():
            stem = os.path.splitext(os.path.basename(feature_path))[0]
            if runner == "cucumber-jvm":
                camel = "".join(w.capitalize() for w in stem.split("-"))
                targets.append(os.path.join(self.steps_dir(), f"{camel}Steps.java"))
            elif runner == "cucumber-js":
                ext = "ts" if self.language == LANG_TS else "js"
                targets.append(os.path.join(self.steps_dir(), f"{stem}.steps.{ext}"))
            else:
                snake = stem.replace("-", "_")
                targets.append(os.path.join(self.steps_dir(), f"{snake}_steps.py"))
        if runner == "cucumber-jvm" and targets:
            targets.append("src/test/java/sdlc/RunCucumberTest.java")
        return targets

    def coding_prompt_fragment(self) -> str:
        runner = self.resolve_runner()
        base = (
            f"Generate {runner} step definitions in `{self.steps_dir()}/` for EVERY "
            "Given/When/Then step in the Gherkin feature files. Step definitions must "
            "import and exercise the real application code (no mocks of the system "
            "under test) and make concrete assertions. The feature files will be "
            f"executed with `{self.resolve_command()}` and must pass."
        )
        if runner == "cucumber-jvm":
            base += (
                " Also generate a JUnit Cucumber runner class "
                "`src/test/java/sdlc/RunCucumberTest.java` pointing at the "
                f"`{FEATURE_DIR}` features directory and the steps glue package."
            )
        return base

    # --- verification -------------------------------------------------------

    def resolve_command(self) -> str:
        if self.profile_config.command:
            return self.profile_config.command
        runner = self.resolve_runner()
        if runner == "cucumber-jvm":
            return java_test_command(self.language)
        if runner == "cucumber-js":
            cmd = f"npx cucumber-js {FEATURE_DIR} --require {self.steps_dir()}"
            if self.language == LANG_TS:
                cmd += " --require-module ts-node/register"
            return cmd
        return f"python3 -m behave {FEATURE_DIR} -f plain"

    def preflight(self) -> tuple[bool, str]:
        if self.profile_config.command:
            return True, "Custom verifier command configured"
        runner = self.resolve_runner()
        probes = {
            "behave": ("python3 -m behave --version",
                       "behave is not installed. Install with: pip install behave, "
                       "or set profiles.\"gherkin-bdd\".command in sdlc.config.json"),
            "cucumber-js": ("npx --no-install cucumber-js --version",
                            "@cucumber/cucumber is not installed. Install with: "
                            "npm install --save-dev @cucumber/cucumber, "
                            "or set profiles.\"gherkin-bdd\".command in sdlc.config.json"),
            "cucumber-jvm": ("mvn -v" if self.language == "java-maven" else "gradle -v",
                             "Build tool not available for cucumber-jvm. Ensure mvn/gradle is "
                             "on PATH and cucumber-jvm is a test dependency, "
                             "or set profiles.\"gherkin-bdd\".command in sdlc.config.json"),
        }
        probe, message = probes.get(runner, (None, None))
        if probe is None:
            return False, (
                f"Unknown gherkin-bdd runner '{runner}'. "
                "Valid runners: behave, cucumber-js, cucumber-jvm."
            )
        if command_available(probe):
            return True, f"{runner} is available"
        return False, message
