import glob
import json
import os
import re

from gates.gate_runner import GateCheck
from utils.toolchain import (
    LANG_JAVA_MAVEN, LANG_TS, is_java, is_js, java_test_command,
)
from profiles.base import SpecProfile, command_available

SPEC_DIR = "sdlc/requirements/var-examples"
VAR_CONFIG_PATH = "var.config.json"
SPEC_DELIMITER = r'^---VAR_SPEC_FILE:\s*([\w\-]+\.md)---\s*$'
FIRST_FENCED_BLOCK = re.compile(r'```(?:\w+)?\s*\n(.*?)```', re.DOTALL)


class VarSpecProfile(SpecProfile):
    """Specs as plain Markdown ("oaths"), verified by running the Vár
    adapter for the project's test framework (pytest-var / cucumber-js-style
    var-cli / var-junit) — pass/fail is the runner's exit code.

    Unlike Gherkin, there is no keyword dialect: a sentence in the Markdown
    is a checkable claim, bound to a stimulus/sensor step by matching its
    text (Cucumber Expressions), not by a Given/When/Then keyword.
    """

    name = "var-spec"
    display_name = "Vár Spec"

    # --- toolchain -----------------------------------------------------

    def resolve_runner(self) -> str:
        if self.profile_config.runner:
            return self.profile_config.runner
        if is_java(self.language):
            return "var-junit"
        if is_js(self.language):
            return "var-cli"
        return "pytest-var"

    def steps_dir(self) -> str:
        if self.profile_config.steps_dir:
            return self.profile_config.steps_dir
        runner = self.resolve_runner()
        if runner == "var-junit":
            return "src/test/java/sdlc/varsteps"
        return os.path.join(SPEC_DIR, "steps")

    # --- requirements stage ----------------------------------------------

    def spec_prompt_fragment(self) -> str:
        return (
            "### Vár Spec Files (one per feature area)\n"
            "- Create separate `.md` files for each distinct feature area, plain "
            "Markdown — NOT Gherkin, no Given/When/Then keywords required\n"
            "- Each file MUST have a `#` heading naming the feature and at least one "
            "concrete example: prose sentences that state literal, checkable values "
            "(e.g. 'The total is 42.' not 'The total is correct.')\n"
            "- Every claim sentence will be bound to a real stimulus/sensor step and "
            "run by a Vár adapter, so avoid vague or unobservable claims\n"
            "- Do NOT use emphasis, links, or inline code inside a claim sentence — "
            "matching is byte-exact against the raw text, so markup inside a matched "
            "sentence breaks the match. Narration around the claims may use any markup\n"
            "- Use this delimiter between files: `---VAR_SPEC_FILE: <name>.md---`\n"
            "- File names should be kebab-case, e.g. `user-authentication.md`\n\n"
            "Spec file output format:\n"
            "---VAR_SPEC_FILE: <name>.md---\n"
            "```markdown\n"
            "[Markdown content here]\n"
            "```\n"
        )

    def parse_and_write(self, llm_content: str) -> list[str]:
        os.makedirs(SPEC_DIR, exist_ok=True)
        segments = re.split(SPEC_DELIMITER, llm_content, flags=re.MULTILINE)
        written = []
        i = 0
        while i < len(segments):
            segment = segments[i].strip()
            if segment.endswith(".md") and i + 1 < len(segments):
                code_block = segments[i + 1].strip()
                # As with gherkin-bdd: only the FIRST fenced block after the
                # marker belongs to this spec file — later profiles' fenced
                # blocks in the same LLM response must not bleed in.
                fence_match = FIRST_FENCED_BLOCK.search(code_block)
                if fence_match:
                    code_content = fence_match.group(1).strip()
                    filepath = os.path.join(SPEC_DIR, segment)
                    with open(filepath, "w") as f:
                        f.write(code_content)
                    written.append(filepath)
                    i += 2
                    continue
            i += 1
        if written:
            self._write_var_config()
        return written

    def spec_artifacts(self) -> list[str]:
        return sorted(glob.glob(os.path.join(SPEC_DIR, "*.md")))

    def requirements_gate_checks(self) -> list[GateCheck]:
        def _check() -> tuple[bool, str]:
            files = self.spec_artifacts()
            if not files:
                return False, f"No .md spec files found in {SPEC_DIR}/"
            for f in files:
                if os.path.getsize(f) == 0:
                    return False, f"Spec file {f} is empty"
            return True, f"{len(files)} spec file(s) found"
        return [GateCheck("var_spec_files_exist", "At least one Vár spec file exists", _check)]

    # --- var.config.json -----------------------------------------------

    def _var_config_entry(self) -> dict:
        docs_glob = os.path.join(SPEC_DIR, "**", "*.md")
        runner = self.resolve_runner()
        if runner == "var-junit":
            # The JVM port has no CLI/globs yet: steps are listed by
            # fully-qualified class name, one per spec file.
            steps = [self._java_step_class_fqn(p) for p in self.spec_artifacts()]
        else:
            ext = "ts" if self.language == LANG_TS else ("js" if is_js(self.language) else "py")
            steps = [os.path.join(self.steps_dir(), f"**/*.steps.{ext}")]
        return {"docs": {"include": [docs_glob], "exclude": []}, "steps": steps}

    def _write_var_config(self):
        with open(VAR_CONFIG_PATH, "w") as f:
            json.dump(self._var_config_entry(), f, indent=2)
            f.write("\n")

    def _java_step_class_fqn(self, spec_path: str) -> str:
        stem = os.path.splitext(os.path.basename(spec_path))[0]
        camel = "".join(w.capitalize() for w in stem.split("-"))
        return f"sdlc.varsteps.{camel}Steps"

    # --- coding stage ------------------------------------------------------

    def coding_scaffold_targets(self, arch_targets: list[str]) -> list[str]:
        targets = []
        runner = self.resolve_runner()
        for spec_path in self.spec_artifacts():
            stem = os.path.splitext(os.path.basename(spec_path))[0]
            if runner == "var-junit":
                camel = "".join(w.capitalize() for w in stem.split("-"))
                targets.append(os.path.join(self.steps_dir(), f"{camel}Steps.java"))
            elif runner == "var-cli":
                ext = "ts" if self.language == LANG_TS else "js"
                targets.append(os.path.join(self.steps_dir(), f"{stem}.steps.{ext}"))
            else:
                snake = stem.replace("-", "_")
                targets.append(os.path.join(self.steps_dir(), f"{snake}.steps.py"))
        if runner == "var-junit" and targets:
            targets.append("src/test/java/sdlc/RunVarSpecsTest.java")
        return targets

    def coding_prompt_fragment(self) -> str:
        runner = self.resolve_runner()
        base = (
            f"Generate {runner} step definitions in `{self.steps_dir()}/` binding "
            "EVERY checkable claim sentence in the Vár spec files. Classify each step "
            "as a stimulus (arranges/acts, evolves typed state functionally) or a "
            "sensor (read-only, returns the value Vár compares against the literal in "
            "the Markdown) — never by a Given/When/Then keyword. Keep steps thin (a "
            "couple of lines) and delegate to the real application code (no mocks of "
            f"the system under test). The specs will be executed with "
            f"`{self.resolve_command()}` and must pass."
        )
        if runner == "var-junit":
            base += (
                " Also generate a JUnit suite class `src/test/java/sdlc/RunVarSpecsTest.java` "
                'with `@Suite @IncludeEngines("var") @SelectDirectories(".")`, and list each '
                f"step class by fully-qualified name in `{VAR_CONFIG_PATH}`'s `steps` array."
            )
        return base

    # --- verification -------------------------------------------------------

    def resolve_command(self) -> str:
        if self.profile_config.command:
            return self.profile_config.command
        runner = self.resolve_runner()
        if runner == "var-junit":
            return java_test_command(self.language)
        if runner == "var-cli":
            return "npx var run"
        return "python3 -m pytest"

    def preflight(self) -> tuple[bool, str]:
        if self.profile_config.command:
            return True, "Custom verifier command configured"
        runner = self.resolve_runner()
        probes = {
            "pytest-var": ("python3 -c \"import pytest_var\"",
                           "pytest-var is not installed. Install with: "
                           "pip install pytest-var, "
                           "or set profiles.\"var-spec\".command in sdlc.config.json"),
            "var-cli": ("npx --no-install var --version",
                        "@oselvar/var-cli is not installed. Install with: "
                        "npm install --save-dev @oselvar/var @oselvar/var-cli, "
                        "or set profiles.\"var-spec\".command in sdlc.config.json"),
            "var-junit": ("mvn -v" if self.language == LANG_JAVA_MAVEN else "gradle -v",
                          "Build tool not available for var-junit. Ensure mvn/gradle is "
                          "on PATH, com.oselvar:var-junit is a test dependency, and "
                          "RunVarSpecsTest.java exists, or set "
                          "profiles.\"var-spec\".command in sdlc.config.json"),
        }
        probe, message = probes.get(runner, (None, None))
        if probe is None:
            return False, (
                f"Unknown var-spec runner '{runner}'. "
                "Valid runners: pytest-var, var-cli, var-junit."
            )
        if command_available(probe):
            return True, f"{runner} is available"
        return False, message
